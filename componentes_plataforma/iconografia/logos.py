"""Logos de acciones/ETF: del código Reuters de XM (RIC) al ticker de la fuente de logos, y comprobación
(con caché) de que la imagen existe."""
import re
import time
import urllib.request

from componentes_plataforma.iconografia.datos import (BOLSA_SUFIJO, BOLSAS_CLASE, BOLSAS_MENOS_UNA, LOGO_ACCION,
                                          RIC_A_TICKER)

_LOGO_OK: dict = {}        # símbolo -> url (acierto: se guarda para siempre)
_LOGO_FALLO: dict = {}     # símbolo -> instante del último fallo (se reintenta)
_REINTENTO_LOGO = 120      # s


def ticker_logo(simbolo: str) -> str:
    """Código Reuters de XM -> ticker de la fuente de logos.
    NVDA.OQ -> NVDA · TU -> TU · ADSGn.DE -> ADS.DE · VOWG_p.DE -> VOW3.DE ·
    UHR.S -> UHR.SW · PEABb.ST -> PEAB-B.ST."""
    base, _, bolsa = (simbolo or "").partition(".")
    bolsa = bolsa.upper()
    pref = bool(re.search(r"_p$", base))                 # acción preferente
    base = re.sub(r"_[a-z]+$", "", base)
    if bolsa in ("DE", "F"):
        # Xetra: el RIC agrega 'G' (+ minúsculas): ADSGn -> ADS, VOWG -> VOW
        base = re.sub(r"[a-z]+$", "", base)
        if base.endswith("G") and len(base) > 2:
            base = base[:-1]
        if pref and not base[-1:].isdigit():
            base += "3"                                  # preferentes: VOW3, JUN3
    elif bolsa in BOLSAS_CLASE and re.search(r"[a-z]$", base):
        base = base[:-1] + "-" + base[-1].upper()        # PEABb -> PEAB-B
    else:
        base = re.sub(r"[a-z]+$", "", base)
    return base + BOLSA_SUFIJO.get(bolsa, "." + bolsa if bolsa else "")


def url_existe(url: str, clave: str) -> str:
    """Devuelve `url` si responde como imagen, "" si no (misma caché que logos)."""
    if clave in _LOGO_OK:
        return _LOGO_OK[clave]
    if time.time() - _LOGO_FALLO.get(clave, 0) < _REINTENTO_LOGO:
        return ""
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            if r.status == 200 and "image" in r.headers.get("Content-Type", ""):
                _LOGO_OK[clave] = url
                return url
    except Exception:
        pass
    _LOGO_FALLO[clave] = time.time()
    return ""


def url_logo_accion(simbolo: str) -> str:
    """URL del logo de una acción/ETF ("" si la fuente no lo tiene). Un <img>
    sin logo se vería como imagen rota, por eso se verifica antes.
    Candidatos en orden: excepción conocida (RIC_A_TICKER) o conversión del
    RIC; en Viena/Helsinki además el RIC sin la letra extra (OMVV.VI -> OMV.VI).
    Caché en `url_existe`: aciertos permanentes, fallos reintentados cada 2 min
    (hallazgo: antes un fallo por demora en el arranque quedaba para siempre)."""
    ticker = RIC_A_TICKER.get(simbolo) or ticker_logo(simbolo)
    candidatos = [ticker]
    base, _, bolsa = ticker.partition(".")
    if bolsa in BOLSAS_MENOS_UNA and simbolo not in RIC_A_TICKER and len(base) > 2:
        candidatos.append(base[:-1] + "." + bolsa)
    for t in candidatos:
        url = url_existe(LOGO_ACCION.format(t), "logo:" + t)
        if url:
            return url
    return ""
