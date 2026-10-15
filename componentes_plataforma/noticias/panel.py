"""Panel de noticias estilo Investing.com: arma la página (modal de la noticia abierta + contenido que se
refresca cada 30 s)."""
from types import ModuleType
from typing import Optional

import streamlit as st

from componentes_plataforma.noticias.modal import abrir_modal
from componentes_plataforma.noticias.secciones import render_contenido


def renderizar_panel_noticias(main: Optional[ModuleType] = None):
    # Si hay una noticia seleccionada, se abre el modal desde el flujo principal
    # (no desde un fragmento) para que funcione correctamente.
    if st.session_state.get("noticia_abierta") is not None:
        abrir_modal(st.session_state["noticia_abierta"])

    @st.fragment(run_every="30s")
    def _contenido():
        render_contenido()
    _contenido()
