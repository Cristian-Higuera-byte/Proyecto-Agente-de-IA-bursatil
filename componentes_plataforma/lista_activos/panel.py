"""Lista de activos del USUARIO (los de su watchlist de Supabase) con scroll, favoritos y botón para agregar."""
import streamlit as st

from componentes_plataforma.lista_activos.estilos import CSS
from componentes_plataforma.lista_activos.fila import dibujar_fila

# Altura (px) de la zona con scroll de la lista
ALTURA_LISTA = 640


def renderizar_watchlist():
    # Lista de activos del USUARIO (los que tenga en su watchlist de Supabase)
    info_activos_real = st.session_state.get("datos_mercado_real", {})
    tickers_watchlist = st.session_state.get("watchlist_simbolos") or list(info_activos_real.keys())

    st.markdown(CSS, unsafe_allow_html=True)

    if "activo_seleccionado" not in st.session_state:
        st.session_state.activo_seleccionado = "EURUSD..."

    with st.container(key="wl_panel"):
        # Encabezado
        st.markdown(
            """
            <div class='wl-head'>
                <div class='ic'><span class='wl-mi'>show_chart</span></div>
                <div>
                    <div class='wl-title'>Lista de activos</div>
                    <div class='wl-sub'>Precios de activos en tiempo real</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Contenedor con altura fija y scroll vertical individual
        with st.container(height=ALTURA_LISTA, border=False, key="wl_scroll"):
            for ticker in tickers_watchlist:
                item = info_activos_real.get(ticker, {
                    "nombre": ticker,
                    "precio": 1.0000,
                    "var": "+0.00 (0.00%)",
                    "sube": True
                })
                dibujar_fila(ticker, item)

        with st.container(key="wl_add"):
            if st.button("Agregar activo", icon=":material/add:", width="stretch"):
                from componentes_plataforma.buscador import abrir_buscador
                abrir_buscador()
                st.rerun()  # app scope: para que aplicacion.py renderice el diálogo
