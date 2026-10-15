"""Enrutado: qué vista se dibuja en el área de contenido según la barra lateral."""
import streamlit as st

from componentes_plataforma.noticias_panel import renderizar_panel_noticias

from .vista_operativa import renderizar_vista_operativa


def renderizar_vista(fragmentos, consola) -> None:
    """Área de contenido principal — cambia según la vista de la barra lateral."""
    st.markdown("<div style='height: 0.2rem'></div>", unsafe_allow_html=True)

    _nav = st.session_state.get("nav_activo")
    if _nav == "noticias":
        # --- VISTA DE NOTICIAS ---
        renderizar_panel_noticias(consola)
    elif _nav == "cotizaciones":
        # --- VISTA DE COTIZACIONES (tablas estilo Investing) ---
        from componentes_plataforma.mercados_panel import renderizar_panel_mercados
        renderizar_panel_mercados(consola)
    elif _nav == "copytrading":
        # --- VISTA COPY TRADING (estrategias, MVP mock) ---
        from componentes_plataforma.copytrading_panel import renderizar_panel_copytrading
        renderizar_panel_copytrading(consola)
    elif _nav == "trading":
        # --- VISTA TRADING (favoritos + watchlist + gráfico + ticket de orden) ---
        renderizar_vista_operativa(fragmentos.watchlist, fragmentos, consola)
    elif _nav == "portafolio":
        # --- VISTA CARTERA (igual a Trading, pero la lista izquierda son las
        #     posiciones abiertas en vez del watchlist) ---
        renderizar_vista_operativa(fragmentos.cartera, fragmentos, consola)
    elif _nav == "resumen":
        # --- VISTA RESUMEN (dashboard del portafolio: KPIs + curva + exposición) ---
        from componentes_plataforma.resumen_panel import renderizar_panel_resumen
        renderizar_panel_resumen(consola)
    elif _nav == "journal":
        # --- VISTA DIARIO (trading journal: operaciones + métricas + notas) ---
        from componentes_plataforma.diario_panel import renderizar_panel_journal
        renderizar_panel_journal(consola)
    else:
        # --- VISTA INICIO (panel de cuenta estilo XM) — también para botones sin vista propia ---
        from componentes_plataforma.inicio_panel import renderizar_panel_inicio
        renderizar_panel_inicio(consola)
