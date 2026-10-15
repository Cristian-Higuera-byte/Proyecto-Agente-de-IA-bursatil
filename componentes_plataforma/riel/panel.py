"""Rail de iconos FIJO a la derecha: dibuja los paneles (Operar, DOM), el rail y el script que los alterna."""
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from componentes_plataforma._estaticos import texto
from componentes_plataforma.riel.datos import BOTONES
from componentes_plataforma.riel.estilos import css

_JS = "\n<script>\n" + texto(Path(__file__).parent / "riel.js") + "</script>\n"


def inyectar_css_rail():
    """Inyecta el CSS del rail. Debe llamarse ANTES de dibujar el gráfico, para que
    éste se mida con el espacio ya reservado a la derecha (si no, queda recortado)."""
    st.markdown(css(), unsafe_allow_html=True)


def renderizar_rail_y_paneles(main=None):
    # Paneles: se dibujan SIEMPRE (el CSS muestra el activo y oculta el resto).
    with st.container(key="pj_panel_order"):
        from componentes_plataforma.panel_orden import renderizar_panel_orden
        renderizar_panel_orden(main)
    with st.container(key="pj_panel_dom"):
        from componentes_plataforma.profundidad_panel import renderizar_panel_dom
        renderizar_panel_dom()

    # Rail de iconos (mismo estilo que el nav izquierdo: solo el ícono).
    with st.container(key="pj_rail"):
        for icono, pid, _nom in BOTONES:
            st.button(icono, key=f"rail_{pid}")

    # Script que alterna los paneles sin reejecutar Python.
    with st.container(key="pj_railjs"):
        components.html(_JS, height=0, width=0)
