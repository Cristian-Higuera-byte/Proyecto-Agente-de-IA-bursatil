"""Datos de la cuenta MT5 y barra superior fija."""
import streamlit as st

from componentes_plataforma.navegacion_superior import renderizar_barra_navegacion as renderizar_nav_superior


def datos_cuenta():
    """(saldo, moneda, P/G flotante, métricas de la barra) para la barra superior."""
    from herramientas.puente_mt5 import inicializar_mt5, obtener_info_cuenta
    inicializar_mt5()
    info = obtener_info_cuenta()
    saldo = info.get("equity") if "error" not in info else None
    moneda = info.get("currency", "USD") if "error" not in info else "USD"
    pl = info.get("profit") if "error" not in info else None  # P/G flotante

    # Métricas ligeras de la barra superior (Riesgo · Drawdown · Mercado). No lee el
    # historial de deals, así que es barata; el símbolo activo define el estado de mercado.
    try:
        from herramientas.estadisticas_portafolio import metricas_barra
        metricas = metricas_barra(st.session_state.get("activo_seleccionado"))
    except Exception:   # la barra nunca debe romper la app por estas métricas
        metricas = None
    return saldo, moneda, pl, metricas


def renderizar_barra_superior(usuario: dict, saldo, moneda, pl, metricas) -> None:
    """Barra superior fija.

    El desplazamiento de la barra según el ancho de la barra lateral (70px / 220px) lo hace el CSS
    de componentes_plataforma/barra_lateral (clase html.pj-sb-exp: animado, sin reejecutar Python)."""
    with st.container(key="barra_nav_fija"):
        renderizar_nav_superior(
            usuario=usuario.get("nombre", "Usuario"),
            saldo=saldo,
            moneda=moneda,
            pl=pl,
            metricas=metricas,
        )
