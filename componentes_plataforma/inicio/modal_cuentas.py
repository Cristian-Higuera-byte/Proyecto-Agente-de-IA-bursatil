"""Modal "Seleccione cuenta" (MT5 expone solo la cuenta conectada en el terminal)."""
import streamlit as st

from componentes_plataforma.inicio.estilos import CSS
from componentes_plataforma.inicio.formato import fmt
from herramientas.puente_mt5 import obtener_info_cuenta


def _cerrar_modal_cuentas():
    st.session_state.ini_modal_cuentas = False


@st.dialog("Seleccione cuenta", on_dismiss=_cerrar_modal_cuentas)
def modal_cuentas():
    info = obtener_info_cuenta()
    st.html(CSS)
    if "error" in info:
        st.warning("No hay conexión con MetaTrader 5.")
        return
    tipo = info.get("tipo", "Demo")
    cls_tipo = "selc-real" if tipo == "Real" else "selc-demo"
    st.html(
        "<div class='selc-card activa'><div class='selc-top'>"
        "<div><div style='color:#e6edf3;font-weight:700;'>Standard</div>"
        f"<div class='selc-bal'>{fmt(info.get('equity', 0))}</div>"
        f"<div class='selc-meta'>#{info.get('login','—')} · Standard · MT5 · "
        f"{info.get('servidor','')}</div></div>"
        f"<span class='selc-tipo {cls_tipo}'>{tipo}</span>"
        "</div></div>"
    )
    st.caption("MetaTrader 5 muestra solo la cuenta conectada en el terminal.")
    if st.button("Crear nueva cuenta", icon=":material/add:", width="stretch", key="selc_crear"):
        st.toast("Para agregar otra cuenta, inicia sesión con ella en el terminal MT5.")
