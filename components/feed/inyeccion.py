"""Inyección del script del feed en la página de Streamlit."""
import streamlit as st
import streamlit.components.v1 as components

from components.feed.ensamblador import script_feed
from components.feed.servidor import API_URL, feed_activo


def inyectar_feed():
    """Inserta (una vez por página) el script del feed en vivo. No ocupa espacio."""
    if not feed_activo():
        return
    # OJO: el CSS que oculta este contenedor (.st-key-pj_feed) va en el bloque de
    # estilos global de app.py. Un st.markdown(_CSS) propio aquí agregaba un
    # elemento más al flujo y Streamlit le sumaba ~1rem de separación (hueco
    # visible bajo la barra superior).
    with st.container(key="pj_feed"):
        components.html(script_feed(API_URL), height=0)
