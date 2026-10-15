"""Vista "Copy trading" estilo XM (MVP con datos SIMULADOS/mock mientras se define la fuente de datos real).
Dos vistas: listado de estrategias (tarjetas) y ficha de detalle de una estrategia. No ejecuta operaciones.
Referencias en referencias/copytrading/*.png."""
from pathlib import Path

import streamlit as st

from componentes_plataforma import _estaticos
from componentes_plataforma.copytrading.datos import CATEGORIAS, ESTRATEGIAS, ORDEN, TABS, por_id
from componentes_plataforma.copytrading.ficha import ficha
from componentes_plataforma.copytrading.tarjeta import tarjeta_html

_CSS = Path(__file__).parent / "estilos.css"


def renderizar_panel_copytrading(main=None):
    st.html(_estaticos.estilos(_CSS))
    if "ct_estrategia" not in st.session_state:
        st.session_state.ct_estrategia = None

    with st.container(key="ct_wrap"):
        # --- Detalle ---
        sel = st.session_state.get("ct_estrategia")
        if sel:
            e = por_id(sel)
            if e:
                ficha(e)
                return

        # --- Listado ---
        st.html("<div class='ct-title'>Copy trading</div>")
        tab = st.segmented_control("Orden", TABS, default=TABS[0],
                                   label_visibility="collapsed", key="ct_tab") or TABS[0]
        cat = st.pills("Categoría", CATEGORIAS, default="Cualquiera",
                       label_visibility="collapsed", key="ct_cat") or "Cualquiera"

        lista = [e for e in ESTRATEGIAS if cat == "Cualquiera" or e["cat"] == cat]
        lista = sorted(lista, key=ORDEN.get(tab, ORDEN["Destacadas"]))
        st.caption(f"{len(lista)} estrategias")

        # grid de 3 columnas
        for fila in range(0, len(lista), 3):
            cols = st.columns(3, gap="medium")
            for j, e in enumerate(lista[fila:fila + 3]):
                with cols[j]:
                    with st.container(key=f"ctrow_{e['id']}"):
                        st.html(tarjeta_html(e))
                        if st.button("ver", key=f"ctsel_{e['id']}"):
                            st.session_state.ct_estrategia = e["id"]
                            st.rerun()
