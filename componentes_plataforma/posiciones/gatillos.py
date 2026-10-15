"""Botones invisibles que pulsa el gráfico: ✕ de cada posición (abre el modal de cierre) y selector de activo."""
import streamlit as st

from componentes_plataforma.flujo_vivo import intervalo
from herramientas.puente_mt5 import obtener_posiciones


def neto(p: dict) -> float:
    return round(float(p.get("profit", 0) or 0) + float(p.get("swap", 0) or 0), 2)


@st.fragment(run_every=intervalo("2s", "5s"))   # altas/bajas de posiciones
def gatillos_cierre():
    """Botones invisibles (uno por posición abierta) que pulsa la ✕ del gráfico."""
    try:
        posiciones = obtener_posiciones() or []
    except Exception:
        posiciones = []
    with st.container(key="chcls_wrap"):
        for p in posiciones:
            tk = p.get("ticket")
            if st.button("cerrar", key=f"chcls_{tk}"):
                st.session_state.ca_cerrar = {
                    "ticket": tk, "symbol": (p.get("symbol") or "").replace("...", ""),
                    "profit": neto(p), "tipo": p.get("tipo"), "volumen": p.get("volumen", 0),
                }
                st.session_state.pop("ca_result", None)
                st.rerun(scope="app")
        # Cambio de activo desde el gráfico en pantalla completa: la lista que muestra el gráfico (watchlist) la deja
        # componentes_plataforma/grafico/panel.py en la sesión; el botón nº i la pulsa el JS del gráfico (selector de activo).
        for i, ticker in enumerate(st.session_state.get("_grafico_lista_activos", [])):
            if st.button("activo", key=f"chcls_sel_{i}"):
                st.session_state.activo_seleccionado = ticker
                st.rerun(scope="app")
