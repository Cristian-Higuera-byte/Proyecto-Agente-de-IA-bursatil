"""Ventana "One-Click Trading": renuncia de responsabilidades (terminos.html) con Cancelar / Acepto."""
from pathlib import Path

import streamlit as st

from componentes_plataforma._estaticos import estilos, texto
from componentes_plataforma.operacion_un_clic.estado import aceptar, cancelar

_DIR = Path(__file__).parent
TEXTO = texto(_DIR / "terminos.html")
CSS = estilos(_DIR / "estilos.css")


@st.dialog("One-Click Trading", width="large", on_dismiss=cancelar)
def _dialogo():
    with st.container(key="oct_root"):
        st.html(CSS)
        st.html(TEXTO)
        c1, c2 = st.columns([1, 1.4])
        with c1:
            if st.button("Cancelar", key="oct_cancel", width="stretch", on_click=cancelar):
                st.rerun()
        with c2:
            with st.container(key="oct_ok"):
                if st.button("Acepto los Términos y Condiciones", key="oct_ok_btn",
                             width="stretch", on_click=aceptar):
                    st.toast("One-Click Trading activado.", icon=":material/bolt:")
                    st.rerun()


def render_modal_terminos():
    """Llamar desde aplicacion.py (fuera de los fragmentos en vivo)."""
    if st.session_state.get("oct_terminos"):
        _dialogo()
