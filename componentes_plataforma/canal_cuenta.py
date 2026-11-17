# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# --------------------------------- INICIO Piña y Jara canal_cuenta .PY ---------------------------------
# -------------------------------------------------------------------------------------------------------

"""
canal_cuenta.py
---------------
Secreto del canal PRIVADO por el que el feed en vivo le entrega el saldo y las posiciones de la cuenta al gráfico de la MISMA sesión (V12 de la auditoría).

Antes el feed reenviaba cada mensaje, con el saldo y las posiciones incluidos, por un `BroadcastChannel` de nombre fijo (`pj-ticks`). Un BroadcastChannel lo comparten todas las pestañas del mismo
origen y navegador: otra pestaña (de otra cuenta, demo o real, o de otra persona en el mismo equipo) recibía el saldo y las posiciones de esta, y podía publicar mensajes que cambiaban las posiciones
dibujadas en el gráfico. Ahora los precios (públicos) siguen yendo por `pj-ticks`, pero el saldo y las posiciones van por un canal cuyo nombre lleva un secreto de ESTA sesión de Streamlit y la cuenta
que se está viendo (`pj-cuenta-<secreto>-<demo|real>`): solo lo conocen los componentes de esta página, que reciben el secreto dentro de su propio código, y otra pestaña no puede escuchar ni escribir.
"""
import secrets

import streamlit as st

# Clave de st.session_state con el secreto de la sesión
_CLAVE = "_canal_cuenta_secreto"


# TITULO CANAL DE LA SESION

def canal_de_la_sesion() -> str:
    """Secreto del canal privado de esta sesión de Streamlit: aleatorio, distinto en cada sesión y estable mientras la sesión viva (si cambiara en cada ejecución los componentes se recargarían)."""
    try:
        if not st.session_state.get(_CLAVE):
            st.session_state[_CLAVE] = secrets.token_urlsafe(18)
        return st.session_state[_CLAVE]
    except Exception:  # noqa: BLE001 - fuera de una sesión de Streamlit (pruebas, herramientas): un secreto nuevo, que nadie más conoce
        return secrets.token_urlsafe(18)


# -------------------------------------------------------------------------------------------------------
# ---------------------------------- FIN Piña y Jara canal_cuenta .PY -----------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
