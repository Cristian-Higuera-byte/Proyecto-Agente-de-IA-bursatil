"""Página completa del dashboard, armada en el mismo orden que tenía el antiguo app.py."""
import streamlit as st

from componentes_plataforma.acceso import requerir_login
from componentes_plataforma.barra_lateral import renderizar_barra_navegacion as renderizar_nav_lateral
from componentes_plataforma.datos_mercado import cargar_datos_mercado
from componentes_plataforma.flujo_vivo import inyectar_feed

from .cabecera import datos_cuenta, renderizar_barra_superior
from .dialogos import renderizar_dialogos
from .estilos import css_global, html_pantalla_carga
from .fragmentos import crear_fragmentos
from .vistas import renderizar_vista


def ejecutar(consola) -> None:
    """Dibuja el dashboard. `consola` es el módulo consola_agente (o None si no se pudo importar)."""
    # Configuración inicial de la página
    st.set_page_config(
        page_title="Dashboard agente analitico Piña & Jara",
        page_icon="📈",
        layout="wide"
    )

    # Estilos CSS globales (tema oscuro tipo terminal de trading)
    st.markdown(css_global(), unsafe_allow_html=True)

    # Login (Supabase): protege el acceso al dashboard
    usuario_actual = requerir_login()

    # Overlay de carga a pantalla completa en la primera entrada
    _primera_carga = not st.session_state.get("datos_cargados", False)
    _overlay = st.empty()
    if _primera_carga:
        _overlay.markdown(html_pantalla_carga(), unsafe_allow_html=True)

    # 1. Barra superior fija (saldo MT5 + métricas de riesgo)
    saldo, moneda, pl, metricas = datos_cuenta()
    renderizar_barra_superior(usuario_actual, saldo, moneda, pl, metricas)

    # Feed de precios en vivo (SSE desde servidor_datos.py): pinta los números
    # directo en el navegador ~4 veces por segundo, sin reejecutar Streamlit.
    inyectar_feed()

    # Carga inicial de datos de mercado
    cargar_datos_mercado()

    # Números en vivo (fragmentos)
    fragmentos = crear_fragmentos()

    # Layout principal: barra lateral + contenido
    col_nav, col_main = st.columns([0.5, 11.5], gap="small")

    # 2. Barra lateral izquierda extendida
    with col_nav:
        renderizar_nav_lateral()

    # 3. Área de contenido principal — cambia según la vista de la barra lateral
    with col_main:
        renderizar_vista(fragmentos, consola)

    # Quitamos el overlay de carga una vez renderizado todo
    _overlay.empty()

    renderizar_dialogos()
