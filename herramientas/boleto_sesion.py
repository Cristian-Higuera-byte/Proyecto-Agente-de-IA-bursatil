# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ------------------------------------ INICIO Piña y Jara boleto_sesion .PY -----------------------------
# -------------------------------------------------------------------------------------------------------

"""
boleto_sesion.py
----------------
Cookie de sesión HttpOnly y boleto de un solo uso para entregarla al navegador (V06 y V07 de la auditoría).

Antes la sesión se mantenía con una cookie que escribía JavaScript (visible para cualquier script de la página) y el servidor de datos aceptaba un token de 12 horas que viajaba en la
dirección. Ahora hay UNA sola credencial: la cookie `pj_sesion`, emitida por el servidor de datos con HttpOnly, Secure y SameSite=Lax, que el navegador envía sola tanto a Streamlit
como al servidor de datos (ambos están en el mismo dominio detrás del proxy). El servidor de datos la valida contra la sesión guardada en la base (herramientas/sesion_persistente.py),
así que cerrar la sesión (en este dispositivo, en todos o al cambiar la contraseña) la invalida de inmediato y no queda ningún token vigente que revocar.

Streamlit no puede crear cookies, y JavaScript no puede crear una HttpOnly. Por eso el navegador la pide al servidor de datos con un BOLETO: un texto firmado con `SERVIDOR_SECRETO`
(HMAC-SHA256) que lleva el token de la sesión, vence a los 60 segundos y solo se acepta una vez. El servidor lo canjea en `POST /t/sesion` y responde con la cookie en `Set-Cookie`.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from http.cookies import SimpleCookie
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# Nombre de la cookie de sesión (el mismo que ya usaba la plataforma)
NOMBRE_COOKIE = "pj_sesion"
# Segundos de vida de un boleto
VIDA_BOLETO_S = 60
# Largo máximo de un boleto que el servidor acepta leer
MAX_BOLETO = 2048

# Identificadores de boletos ya canjeados: {identificador: vencimiento}. Vive en el proceso del servidor de datos, que es quien los canjea.
_usados: dict = {}
_CANDADO = threading.Lock()


# TITULO SECRETO

def _secreto() -> Optional[bytes]:
    """Secreto con el que se firman los boletos (`SERVIDOR_SECRETO` del .env, mínimo 32 caracteres), o None si no está configurado."""
    valor = os.environ.get("SERVIDOR_SECRETO", "").strip()
    return valor.encode("utf-8") if len(valor) >= 32 else None


# TITULO CONFIGURADO

def configurado() -> bool:
    """True si hay un secreto válido: sin él no se pueden emitir ni canjear boletos."""
    return _secreto() is not None


# TITULO GENERAR SECRETO

def generar_secreto() -> str:
    """Un secreto aleatorio de 64 caracteres hexadecimales, para pegarlo como SERVIDOR_SECRETO en el .env."""
    return secrets.token_hex(32)


# TITULO B64

def _b64(datos: bytes) -> str:
    """Codifica bytes en base64 seguro para direcciones y sin relleno."""
    return base64.urlsafe_b64encode(datos).decode("ascii").rstrip("=")


# TITULO DEB64

def _deb64(texto: str) -> bytes:
    """Decodifica el base64 que genera `_b64`."""
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


# TITULO FIRMAR

def _firmar(carga: str, secreto: bytes) -> str:
    """Firma HMAC-SHA256 de la carga, en base64."""
    return _b64(hmac.new(secreto, carga.encode("ascii"), hashlib.sha256).digest())


# TITULO EMITIR

def emitir(token_sesion: str, persistente: bool = True) -> str:
    """Emite un boleto de un solo uso que lleva el token de la sesión y si la cookie debe durar (persistente) o morir al cerrar el navegador; devuelve '' si no hay secreto o no hay token."""
    secreto = _secreto()
    if secreto is None or not token_sesion:
        return ""
    datos = {"t": token_sesion, "e": int(time.time()) + VIDA_BOLETO_S, "n": secrets.token_hex(8), "p": 1 if persistente else 0}
    carga = _b64(json.dumps(datos, separators=(",", ":")).encode("utf-8"))
    return f"{carga}.{_firmar(carga, secreto)}"


# TITULO CANJEAR

def canjear(boleto: str) -> Optional[tuple]:
    """Devuelve (token de sesión, persistente) del boleto si es auténtico, no venció y no se había canjeado; si no, None. Un boleto solo se canjea una vez.

    Compara la firma en tiempo constante. Cualquier formato inválido da None, nunca una excepción."""
    secreto = _secreto()
    if secreto is None or not boleto or len(boleto) > MAX_BOLETO or boleto.count(".") != 1:
        return None
    carga, firma = boleto.split(".")
    if not hmac.compare_digest(firma.encode("utf-8", "replace"), _firmar(carga, secreto).encode("ascii")):
        return None
    try:
        datos = json.loads(_deb64(carga))
        vence, nonce, token, persistente = float(datos["e"]), str(datos["n"]), str(datos["t"]), bool(datos.get("p", 1))
    except (ValueError, KeyError, TypeError):
        return None
    ahora = time.time()
    if vence < ahora or not token:
        return None
    with _CANDADO:
        for viejo in [n for n, v in _usados.items() if v < ahora]:
            del _usados[viejo]
        if nonce in _usados:
            return None
        _usados[nonce] = vence
    return token, persistente


# TITULO HUELLA DE LA SESION

def huella_sesion(token_sesion: str) -> str:
    """Resumen corto (16 caracteres hexadecimales) del token de sesión, o '' si no hay: es el identificador de la sesión de este dispositivo (acceso/sesion.py); el token no debe viajar ni guardarse."""
    return hashlib.sha256(token_sesion.encode("utf-8")).hexdigest()[:16] if token_sesion else ""


# TITULO LEER COOKIE

def leer_cookie(cabecera: str) -> str:
    """Valor de la cookie de sesión dentro de una cabecera `Cookie` (cadena vacía si no está o la cabecera no se entiende)."""
    try:
        galleta = SimpleCookie()
        galleta.load(cabecera or "")
        return galleta[NOMBRE_COOKIE].value if NOMBRE_COOKIE in galleta else ""
    except Exception:  # noqa: BLE001 - una cabecera mal formada es «sin cookie»
        return ""


# TITULO CABECERA SET COOKIE

def cabecera_set_cookie(token: str, duracion_s: Optional[int], seguro: bool) -> str:
    """Texto de la cabecera `Set-Cookie` de la cookie de sesión: HttpOnly, SameSite=Lax, Path=/ (sin `Domain`: solo el host que la emitió) y Secure cuando la plataforma va por HTTPS.

    Con `duracion_s` 0 la borra y con None es una cookie de sesión del navegador (sin `Max-Age`: desaparece al cerrarlo)."""
    duracion = "" if duracion_s is None else f"; Max-Age={int(duracion_s)}"
    return f"{NOMBRE_COOKIE}={token}{duracion}; Path=/; HttpOnly; SameSite=Lax" + ("; Secure" if seguro else "")


# -------------------------------------------------------------------------------------------------------
# ------------------------------------- FIN Piña y Jara boleto_sesion .PY -------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
