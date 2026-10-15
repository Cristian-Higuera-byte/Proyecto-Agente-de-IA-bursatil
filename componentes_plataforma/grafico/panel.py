"""Panel central: la cabecera de precio, el gráfico y los botones invisibles de cierre de posiciones."""
from __future__ import annotations

import json
import os
from types import ModuleType
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components

from componentes_plataforma.grafico.cabecera_precio import renderizar_cabecera_precio
from componentes_plataforma.grafico.ensamblador import html_grafico
from componentes_plataforma.grafico.simbolo import info_simbolo, limpiar_simbolo
from componentes_plataforma.posiciones_grafico import gatillos_cierre, js_posiciones
from herramientas.puente_mt5 import inicializar_mt5
from herramientas.gestor_lista_activos import nombre_visible

# URL de la API que sirve las velas al gráfico (/velas y /ultima).
API_URL = os.environ.get("MT5_API_URL", "http://localhost:8000")


def _lista_activos(activo_visible: str) -> str:
    """Activos que ofrece el selector del gráfico en pantalla completa (la watchlist del usuario), como JSON para el JS.
    Deja en la sesión los tickers en el mismo orden: posiciones_grafico.gatillos_cierre() crea un botón oculto por cada
    uno y el JS del gráfico pulsa el nº i para cambiar de activo sin salir de la pantalla completa."""
    info = st.session_state.get("datos_mercado_real") or {}
    tickers = list(st.session_state.get("watchlist_simbolos") or info.keys())
    if not tickers:
        tickers = [st.session_state.get("activo_seleccionado", "EURUSD...")]
    tickers = tickers[:40]
    try:
        from componentes_plataforma.iconos import icono_activo
    except Exception:  # noqa: BLE001 - sin íconos el selector sigue funcionando
        icono_activo = None
    lista = []
    for t in tickers:
        try:
            icono = icono_activo(t, 26) if icono_activo else ""
        except Exception:  # noqa: BLE001
            icono = ""
        lista.append({
            "t": t, "b": nombre_visible(t), "n": str((info.get(t) or {}).get("nombre", "")),
            "i": icono, "a": limpiar_simbolo(t) == activo_visible,
        })
    st.session_state["_grafico_lista_activos"] = tickers
    return json.dumps(lista).replace("</", "<\\/")


def renderizar_panel_central(main: Optional[ModuleType] = None) -> None:
    inicializar_mt5()

    activo_actual = st.session_state.get("activo_seleccionado", "EURUSD...")
    activo_visible = limpiar_simbolo(activo_actual)
    digits, pip = info_simbolo(activo_visible)

    renderizar_cabecera_precio(activo_visible, digits)

    activos_json = _lista_activos(activo_visible)
    html_chart = html_grafico(activo_visible, API_URL, digits, pip, js_posiciones(activo_visible), activos_json)
    components.html(html_chart, height=750)
    gatillos_cierre()   # ✕ de las líneas → modal de cierre
