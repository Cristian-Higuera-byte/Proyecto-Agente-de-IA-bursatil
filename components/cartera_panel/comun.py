"""
cartera_panel/comun.py
----------------------
Helpers compartidos por la lista, el modal de cierre y el detalle: cálculo del P/G
neto, formato de precio, texto del botón de cierre (mismo formato que usa live_feed en
JS) y la carga de los 3 CSS del panel (estatico/lista.css · modal.css · detalle.css).
El CSS se lee una sola vez (lru_cache) y se inyecta con st.markdown (como el original).
"""
from functools import lru_cache
from pathlib import Path

import streamlit as st

_ESTATICO = Path(__file__).resolve().parent / "estatico"

# Selector que acota el CSS del modal al diálogo que contiene el botón de cierre.
_SEL_MODAL = "[data-testid='stDialog']:has([class*='st-key-ca_btncerrar_'])"


@lru_cache(maxsize=None)
def _leer(nombre: str) -> str:
    """Lee un CSS de cartera_panel/estatico/. Cacheado en memoria por proceso."""
    try:
        return (_ESTATICO / nombre).read_text(encoding="utf-8")
    except OSError:
        return ""


def css_lista() -> None:
    st.markdown(f"<style>{_leer('lista.css')}</style>", unsafe_allow_html=True)


def css_detalle() -> None:
    st.markdown(f"<style>{_leer('detalle.css')}</style>", unsafe_allow_html=True)


def css_modal() -> None:
    css = _leer("modal.css").replace("__SEL__", _SEL_MODAL)
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def neto(p: dict) -> float:
    """P/G neto de una posición (profit + swap), como lo suma MT5 en la cuenta."""
    return float(p.get("profit", 0.0) or 0.0) + float(p.get("swap", 0.0) or 0.0)


def fmtp(x) -> str:
    """Precio sin ceros finales (no tenemos los dígitos del símbolo aquí)."""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return (f"{x:,.5f}".rstrip("0").rstrip(".")) if x else "—"


def texto_cerrar(prof: float) -> str:
    """Texto del botón estilo XM: 'Cerrar con pérdida de -$220.00' /
    'Cerrar con ganancia de $280.00'. (live_feed.py usa el mismo formato.)"""
    verbo = "ganancia" if prof >= 0 else "pérdida"
    signo = "-" if prof < 0 else ""
    return f"Cerrar con {verbo} de {signo}${abs(prof):,.2f}"
