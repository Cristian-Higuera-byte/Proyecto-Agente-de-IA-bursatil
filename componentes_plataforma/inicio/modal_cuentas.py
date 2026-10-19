# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# --------------------------------- INICIO Piña y Jara modal_cuentas .PY --------------------------------
# -------------------------------------------------------------------------------------------------------

"""Modal "Seleccione cuenta" (MT5 expone solo la cuenta conectada en el terminal).

Diálogo de Streamlit que muestra la cuenta activa y recuerda cómo agregar otra. Su visibilidad se
controla con `st.session_state.inicio_modal_cuentas`.
"""
import streamlit as st

# Estilos de Inicio (las clases selc-* del diálogo viven en estilos.css).

from componentes_plataforma.inicio.estilos import CSS
# Formato de dinero del equity.
from componentes_plataforma.inicio.formato import formatear_dinero
# Datos de la cuenta conectada en MT5.
from herramientas.puente_mt5 import obtener_info_cuenta


# TITULO CERRAR MODAL CUENTAS

def _cerrar_modal_cuentas():
    """Callback `on_dismiss` del diálogo: apaga la bandera `inicio_modal_cuentas` para que no se reabra en el próximo rerun."""
    st.session_state.inicio_modal_cuentas = False


# TITULO MODAL CUENTAS

@st.dialog("Seleccione cuenta", on_dismiss=_cerrar_modal_cuentas)
def modal_cuentas():
    """Diálogo «Seleccione cuenta»: muestra la cuenta conectada (equity, login, servidor, tipo Demo/Real).

    Decorada con `st.dialog`. Sin conexión a MT5 muestra una advertencia. El botón «Crear nueva cuenta»
    solo informa por toast que hay que iniciar sesión con otra cuenta en el terminal MT5.
    """
    # Datos de la cuenta conectada.
    info = obtener_info_cuenta()
    # Los diálogos se montan fuera del flujo normal, por eso necesitan su propia inyección de estilos.
    st.html(CSS)
    if "error" in info:
        st.warning("No hay conexión con MetaTrader 5.")
        return
    tipo = info.get("tipo", "Demo")
    # Clase de color de la etiqueta Real/Demo.
    cls_tipo = "selector-cuenta-real" if tipo == "Real" else "selector-cuenta-demo"
    # Tarjeta de la cuenta activa.
    st.html(
        "<div class='selector-cuenta-tarjeta activa'><div class='selector-cuenta-superior'>"
        "<div><div style='color:#e6edf3;font-weight:700;'>Standard</div>"
        f"<div class='selector-cuenta-bal'>{formatear_dinero(info.get('equity', 0))}</div>"
        f"<div class='selector-cuenta-meta'>#{info.get('login','—')} · Standard · MT5 · "
        f"{info.get('servidor','')}</div></div>"
        f"<span class='selector-cuenta-tipo {cls_tipo}'>{tipo}</span>"
        "</div></div>"
    )
    st.caption("MetaTrader 5 muestra solo la cuenta conectada en el terminal.")
    if st.button("Crear nueva cuenta", icon=":material/add:", width="stretch", key="selector_cuenta_crear"):
        st.toast("Para agregar otra cuenta, inicia sesión con ella en el terminal MT5.")


# -------------------------------------------------------------------------------------------------------
# ---------------------------------- FIN Piña y Jara modal_cuentas .PY ----------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
