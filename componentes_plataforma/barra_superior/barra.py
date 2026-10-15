"""Barra de navegación superior (estilo terminal de trading): buscador, saldo y métricas, campana y usuario."""
from pathlib import Path

import streamlit as st

from componentes_plataforma._estaticos import texto
from componentes_plataforma.barra_superior.tarjetas import chip, chips_metricas as _calcular_chips
from componentes_plataforma.barra_superior.datos import IC_TEMA
from componentes_plataforma.barra_superior.estilos import CSS
from componentes_plataforma.barra_superior.notificaciones import campana, usuario_id as _usuario_id
from componentes_plataforma.buscador import abrir_buscador
from nucleo_agente import vigilancia

_DIR = Path(__file__).parent


def renderizar_barra_navegacion(usuario: str = "Emilio Fuentes",
                                saldo: float | None = None,
                                moneda: str = "USD",
                                pl: float | None = None,
                                usuario_id: str | None = None,
                                metricas: dict | None = None):
    iniciales = "".join([p[0] for p in usuario.split()[:2]]).upper() or "U"
    try:
        vigilancia.iniciar_motor()   # idempotente: retoma las vigilancias activas tras reiniciar la app
    except Exception:  # noqa: BLE001 - la barra nunca debe fallar por esto
        pass

    # Chip de saldo total de MT5 (equity). Si no hay dato, se muestra "—".
    if saldo is not None:
        saldo_txt = f"${saldo:,.2f} {moneda}"
    else:
        saldo_txt = "— sin conexión MT5"

    # P/G flotante (de posiciones abiertas) junto al saldo, estilo XM.
    # Siempre se dibuja el <span> (aunque esté vacío) para que el feed en vivo
    # (data-pj-acc, ver componentes_plataforma/flujo_vivo.py) pueda rellenarlo.
    pl_txt = f"{pl:+,.2f}" if pl is not None and abs(pl) >= 0.005 else ""
    color_pl = "#3fb950" if (pl or 0) >= 0 else "#f85149"
    pl_span = (
        f"<span data-pj-acc='profit' style='font-size:13px; font-weight:700; color:{color_pl}; "
        f"font-family:monospace;'>{pl_txt}</span>"
    )
    attr_saldo = "data-pj-acc='equity'" if saldo is not None else ""
    # Tarjeta CAPITAL: equity + P/G flotante juntos (estilo XM). El <span
    # data-pj-acc='profit'> lo rellena el feed en vivo (componentes_plataforma/flujo_vivo.py).
    chip_capital = chip(
        "Capital",
        f"<span {attr_saldo} style='font-size:14px; font-weight:700; color:#3fb950; "
        f"font-family:monospace;'>{saldo_txt}</span>{pl_span}",
    )

    chips_metricas = _calcular_chips(metricas)

    # Estilos de la navbar + del botón buscador
    st.markdown(CSS, unsafe_allow_html=True)

    # 4 tarjetas: Capital (equity + P&L) · Riesgo · Drawdown · Mercado.
    html_saldo = f"""
        <div style='display:flex; align-items:center; justify-content:flex-end; gap:7px; white-space:nowrap;'>
            {chip_capital}{chips_metricas}
            <span class='nav-ico' title='Tema' style='margin-left:6px;'>{IC_TEMA}</span>
        </div>
    """

    html_usuario = (texto(_DIR / "usuario_menu.html")
                    .replace("__INICIALES__", iniciales).replace("__USUARIO__", usuario))

    # ☰ + buscador (corto, a la izquierda) + espacio + saldo/tema + campana + usuario
    c_toggle, c_buscar, c_spacer, c_saldo, c_campana, c_usuario = st.columns(
        [0.2, 1.3, 1.49, 1.05, 0.16, 0.6], vertical_alignment="center")
    with c_toggle:
        # El clic lo intercepta un script en el navegador (nav_bar.py, _JS_SIDEBAR)
        # que alterna la barra lateral con animación CSS, SIN reejecutar Python.
        st.button(":material/menu:", key="top_toggle")
    with c_buscar:
        if st.button("Buscar activo, par o ticker...", icon=":material/search:",
                     key="btn_abrir_buscador", width="stretch"):
            abrir_buscador()
            st.rerun()
    with c_spacer:
        st.empty()
    with c_saldo:
        st.markdown(html_saldo, unsafe_allow_html=True)
    with c_campana:
        campana(usuario_id or _usuario_id())
    with c_usuario:
        st.markdown(html_usuario, unsafe_allow_html=True)
