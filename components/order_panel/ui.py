"""
order_panel/ui.py
-----------------
Piezas de UI reutilizables del ticket: carga de los estáticos (CSS) y el "campo tipo
tarjeta" (etiqueta dentro + número grande, estilo XM). El CSS vive en estatico/ticket.css
y se lee una sola vez (cacheado); cargar_css() lo inyecta acotado a las claves .st-key-ord_*.
"""
from functools import lru_cache
from pathlib import Path

import streamlit as st

_ESTATICO = Path(__file__).resolve().parent / "estatico"


@lru_cache(maxsize=None)
def leer_estatico(nombre: str) -> str:
    """Lee un archivo de order_panel/estatico/ (CSS/JS). Cacheado en memoria por proceso."""
    try:
        return (_ESTATICO / nombre).read_text(encoding="utf-8")
    except OSError:
        return ""


def cargar_css() -> None:
    """Inyecta el CSS del ticket (estatico/ticket.css)."""
    st.html(f"<style>{leer_estatico('ticket.css')}</style>")


def campo(clave: str, etiqueta: str, sufijo: str = ""):
    """Contenedor de un campo tipo tarjeta: etiqueta dentro (arriba) + sufijo opcional."""
    cont = st.container(key=f"ord_box_{clave}")
    cont.html(f"<div class='ord-box-lbl'>{etiqueta}</div>"
              + (f"<div class='ord-box-suf'>{sufijo}</div>" if sufijo else ""))
    return cont
