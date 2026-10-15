# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# -------------------------------------- INICIO Piña y Jara rss .PY -------------------------------------
# -------------------------------------------------------------------------------------------------------

"""Lectura de los RSS de Investing.com en español (título, enlace, imagen, fecha), con caché.

Hace peticiones HTTP directas con `urllib` y analiza el XML con `ElementTree`; los resultados se cachean con
`st.cache_data` para no consultar la red en cada rerun.
"""
import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import streamlit as st

from componentes_plataforma.noticias.datos import FUENTES, FUENTES_MAS, PLACEHOLDER


def _limpiar(texto: str) -> str:
    """Quita las etiquetas HTML de un texto, decodifica las entidades (&amp;, etc.) y recorta los espacios.
    Acepta None o vacío y devuelve cadena vacía."""
    return html.unescape(re.sub(r"<[^>]+>", "", texto or "")).strip()


def _fecha_a_ts(pubdate: str) -> float:
    """Convierte la fecha de publicación de un item RSS en una marca de tiempo unix.

    Intenta primero el formato RFC 822 de RSS y luego el formato ISO `AAAA-MM-DD HH:MM:SS` (interpretado en
    UTC). Devuelve 0.0 si la fecha está vacía o no se reconoce."""
    pubdate = (pubdate or "").strip()
    if not pubdate:
        return 0.0
    try:
        return parsedate_to_datetime(pubdate).timestamp()
    except Exception:
        pass
    # Segundo intento: formato ISO truncado a 19 caracteres, con la T cambiada por un espacio
    txt = pubdate[:19].replace("T", " ")
    try:
        return datetime.strptime(txt, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
    except Exception:
        return 0.0


def _fecha_local(ts: float, raw: str) -> str:
    """Formatea la marca de tiempo como `dd-mm-aaaa hh:mm` en hora local; si no hay `ts` o falla, devuelve el
    texto original `raw`."""
    try:
        return datetime.fromtimestamp(ts).strftime("%d-%m-%Y %H:%M") if ts else raw
    except Exception:
        return raw


def _leer_fuentes(fuentes: list[str]) -> list[dict]:
    """Noticias de varios RSS, sin enlaces repetidos y de la más nueva a la más vieja.

    Recibe la lista de URLs. Cada noticia es un diccionario con `title`, `link`, `desc`, `img`, `_ts`
    (marca de tiempo para ordenar) y `fecha` (texto). Una fuente que falla (red o XML inválido) se omite sin
    interrumpir a las demás."""
    # `vistos` evita duplicados entre fuentes por el enlace; `todas` acumula las noticias válidas
    vistos: set[str] = set()
    todas: list[dict] = []
    for url in fuentes:
        try:
            # El User-Agent de navegador evita que el sitio rechace la petición; 8 s de tiempo máximo
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                root = ET.fromstring(r.read())
            for it in root.findall(".//item"):
                titulo = _limpiar(it.findtext("title") or "")
                link = (it.findtext("link") or "").strip()
                # Se descartan items sin título o enlace y los ya vistos
                if not titulo or not link or link in vistos:
                    continue
                vistos.add(link)
                # Imagen: primero `enclosure`, luego `media:content`; si no hay, la imagen de respaldo
                enc = it.find("enclosure")
                media = it.find("{http://search.yahoo.com/mrss/}content")
                img = (enc.get("url") if enc is not None and enc.get("url")
                       else media.get("url") if media is not None and media.get("url")
                       else PLACEHOLDER)
                ts = _fecha_a_ts((it.findtext("pubDate") or "").strip())
                todas.append({
                    "title": titulo,
                    "link": link,
                    "desc": _limpiar(it.findtext("description") or ""),
                    "img": img,
                    "_ts": ts,
                    "fecha": _fecha_local(ts, (it.findtext("pubDate") or "")[:16]),
                })
        except Exception:
            continue
    # Más recientes primero
    todas.sort(key=lambda n: n["_ts"], reverse=True)
    return todas


@st.cache_data(ttl=30, show_spinner=False)
def cargar_noticias() -> list[dict]:
    """Noticias de las fuentes principales (`FUENTES`), cacheadas 30 s. Alimentan la noticia principal y el
    carrusel."""
    return _leer_fuentes(FUENTES)


@st.cache_data(ttl=60, show_spinner=False)
def cargar_mas_noticias() -> list[dict]:
    """'Más noticias': otras categorías de Investing en español (actuales, con foto). Cacheadas 60 s."""
    return _leer_fuentes(FUENTES_MAS)


# -------------------------------------------------------------------------------------------------------
# --------------------------------------- FIN Piña y Jara rss .PY ---------------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
