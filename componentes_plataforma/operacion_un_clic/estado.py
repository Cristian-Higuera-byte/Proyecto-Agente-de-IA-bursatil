"""Estado del interruptor One-Click y de la ventana de términos (callbacks de Streamlit)."""
import streamlit as st

from componentes_plataforma.operacion_un_clic.registro import aceptado, registrar


def al_cambiar():
    """on_change del interruptor: si se activa sin haber aceptado, se apaga y se
    pide aceptar los términos (el modal lo abre aplicacion.py en el rerun completo)."""
    if st.session_state.get("ord_oc") and not aceptado():
        st.session_state.ord_oc = False
        st.session_state.oct_terminos = True
        st.session_state._oct_pedir = True     # una sola vez: rerun de app para abrir el modal


def pedir_terminos_si_corresponde():
    """Llamar dentro del fragmento del ticket, tras el interruptor: si hay que
    mostrar los términos, rerun de la app (el modal se dibuja fuera del fragmento)."""
    if st.session_state.pop("_oct_pedir", False):
        st.rerun(scope="app")


def aceptar():
    registrar()
    st.session_state.ord_oc = True
    st.session_state.oct_terminos = False


def cancelar():
    st.session_state.oct_terminos = False
