"""Panel de Inicio: arma la vista con sus bloques (cuenta, accesos rápidos, posiciones, historial,
promociones y modal de cuentas). Los fragmentos `run_every` se declaran aquí porque su intervalo depende de
si el feed en vivo está activo en ese momento."""
import streamlit as st

from components.inicio.cuenta import dibujar_cuenta
from components.inicio.datos import ACCIONES, PROMOS
from components.inicio.estilos import CSS
from components.inicio.formato import mi
from components.inicio.historial import dibujar_historial
from components.inicio.modal_cuentas import modal_cuentas
from components.inicio.posiciones import dibujar_posiciones
from components.live_feed import intervalo as _intervalo
from tools.mt5_bridge import inicializar_mt5


def renderizar_panel_inicio(main=None):
    inicializar_mt5()
    st.html(CSS)

    if "ini_ocultar" not in st.session_state:
        st.session_state.ini_ocultar = False
    usuario = st.session_state.get("usuario_info") or {}
    nombre = (usuario.get("nombre") if isinstance(usuario, dict) else "") or ""

    # Cuenta (en vivo vía feed; sin recarga periódica si hay feed)
    @st.fragment(run_every=_intervalo("2s"))
    def _cuenta_vivo():
        dibujar_cuenta(nombre)

    # Posiciones abiertas (precio y P/G en vivo por el feed)
    @st.fragment(run_every=_intervalo("2s", "5s"))
    def _posiciones_vivo():
        dibujar_posiciones()

    # Historial de operaciones cerradas. Se refresca cada pocos segundos para que una
    # operación recién cerrada aparezca sola (entran filas nuevas al cerrar posiciones).
    @st.fragment(run_every=_intervalo("8s", "12s"))
    def _historial():
        dibujar_historial()

    # Contenido centrado con ancho máximo
    with st.container(key="ini_wrap"):
        _cuenta_vivo()

        st.html("<div class='ini-sec'><h3>Accesos rápidos</h3></div>")
        acc_cols = st.columns(len(ACCIONES), gap="medium")
        for i, (ic, color, titulo, sub, dest) in enumerate(ACCIONES):
            with acc_cols[i]:
                with st.container(key=f"accrow_{i}"):
                    st.html(
                        f"<div class='acc-card'><div class='acc-ic' style='background:{color}1f;'>"
                        f"{mi(ic, color)}</div><div class='acc-tx'><div class='acc-t'>{titulo}</div>"
                        f"<div class='acc-s'>{sub}</div></div>{mi('chevron_right')}</div>"
                    )
                    if st.button(titulo, key=f"accsel_{i}"):
                        if dest:
                            st.session_state.nav_activo = dest
                            st.rerun()
                        else:
                            st.toast(f"{titulo}: disponible próximamente.")

        _posiciones_vivo()

        _historial()

        st.html("<div class='ini-sec'><h3>Promociones</h3></div>")
        st.html("<div class='promo-grid'>" + "".join(
            f"<div class='promo-card {c}'>{mi(ic, color)}<h4>{t}</h4><p>{d}</p></div>"
            for c, ic, color, t, d in PROMOS) + "</div>")

    # Modal selección de cuenta (fuera de los fragmentos en vivo)
    if st.session_state.get("ini_modal_cuentas"):
        modal_cuentas()
