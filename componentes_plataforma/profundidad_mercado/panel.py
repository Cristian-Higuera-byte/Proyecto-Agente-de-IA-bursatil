"""Panel de profundidad de mercado (DOM): cabecera fija y escalera que se refresca sola.

ESTADO: la escalera se centra en el Bid/Ask EN VIVO del activo (precios reales que se mueven con el mercado),
con VOLÚMENES DE MUESTRA cuando el bróker no publica el libro (en Forex/CFD de XM suele venir vacío). Si el
bróker lo publica (`mt5.market_book_get`), se muestra la profundidad real.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st
from proveedores.selector_mt5 import mt5  # type: ignore[import-untyped]

from componentes_plataforma import _estaticos
from componentes_plataforma.profundidad_mercado import escalera
from componentes_plataforma.flujo_vivo import intervalo
from herramientas.puente_mt5 import (MT5_LOCK, inicializar_mt5, obtener_precio_actual,
                              resolver_simbolo, obtener_dom)

_CSS = Path(__file__).parent / "estilos.css"


def _dibujar_escalera(real: str) -> None:
    """Contenido de la escalera. Se ejecuta como FRAGMENTO (ver renderizar_panel_dom): solo este bloque se refresca."""
    inicializar_mt5()
    t = obtener_precio_actual(real)
    if "error" in t or not (t.get("bid") or t.get("ask")):
        st.caption("Sin precio en vivo. ¿Está abierto MetaTrader 5?")
        return
    bid, ask = float(t.get("bid", 0)), float(t.get("ask", 0))
    try:
        with MT5_LOCK:
            info = mt5.symbol_info(real)
    except Exception:
        info = None
    dig = int(getattr(info, "digits", 5) or 5) if info else 5
    point = (float(getattr(info, "point", 0.0) or 0.0) if info else 0.0) or (10 ** -dig)

    dom = obtener_dom(real, 8)
    if dom.get("disponible"):
        filas, nota = escalera.filas_reales(dom, bid, ask, dig)
    else:
        filas, nota = escalera.filas_demo(bid, ask, dig, point)
    st.html(escalera.html_escalera(filas, nota))


def renderizar_panel_dom():
    st.html(_estaticos.estilos(_CSS))
    with st.container(key="dom_panel"):
        activo = st.session_state.get("activo_seleccionado", "EURUSD...")
        real = resolver_simbolo(activo)
        visible = activo.replace("...", "").strip()
        st.html(f"<div class='dom-h'>Profundidad · {visible}</div>"
                f"<div class='dom-sub'>Libro de órdenes (DOM)</div>")

        # La escalera es un fragmento: se refresca sola cada 2 s (o la actualiza el feed en vivo) sin recargar la
        # página. IMPORTANTE: esta línea es la que dibuja la escalera; sin ella el panel solo muestra el título.
        st.fragment(run_every=intervalo("2s"))(_dibujar_escalera)(real)
