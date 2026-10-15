"""Lectura de los RSS de Investing.com en español (título, enlace, imagen, fecha), con caché."""
import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import streamlit as st

from componentes_plataforma.noticias.datos import FUENTES, FUENTES_MAS, PLACEHOLDER


def _limpiar(texto: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", texto or "")).strip()


def _fecha_a_ts(pubdate: str) -> float:
    pubdate = (pubdate or "").strip()
    if not pubdate:
        return 0.0
    try:
        return parsedate_to_datetime(pubdate).timestamp()
    except Exception:
        pass
    txt = pubdate[:19].replace("T", " ")
    try:
        return datetime.strptime(txt, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
    except Exception:
        return 0.0


def _fecha_local(ts: float, raw: str) -> str:
    try:
        return datetime.fromtimestamp(ts).strftime("%d-%m-%Y %H:%M") if ts else raw
    except Exception:
        return raw


def _leer_fuentes(fuentes: list[str]) -> list[dict]:
    """Noticias de varios RSS, sin enlaces repetidos y de la más nueva a la más vieja."""
    vistos: set[str] = set()
    todas: list[dict] = []
    for url in fuentes:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                root = ET.fromstring(r.read())
            for it in root.findall(".//item"):
                titulo = _limpiar(it.findtext("title") or "")
                link = (it.findtext("link") or "").strip()
                if not titulo or not link or link in vistos:
                    continue
                vistos.add(link)
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
    todas.sort(key=lambda n: n["_ts"], reverse=True)
    return todas


@st.cache_data(ttl=30, show_spinner=False)
def cargar_noticias() -> list[dict]:
    return _leer_fuentes(FUENTES)


@st.cache_data(ttl=60, show_spinner=False)
def cargar_mas_noticias() -> list[dict]:
    """'Más noticias': otras categorías de Investing en español (actuales, con foto)."""
    return _leer_fuentes(FUENTES_MAS)
