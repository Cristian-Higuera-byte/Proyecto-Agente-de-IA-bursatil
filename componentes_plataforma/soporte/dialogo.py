# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ------------------------------------ INICIO Piña y Jara dialogo .PY -----------------------------------
# -------------------------------------------------------------------------------------------------------

"""Ventana «Soporte» que abre el botón del audífono de la barra lateral: reportar un problema, preguntas frecuentes y contacto.

El botón llama a `abrir` (un callback, que marca la ventana como abierta) y `renderizar_modal_soporte` la dibuja al final de la página, fuera de los fragmentos en vivo,
igual que los demás diálogos. El reporte lo envía herramientas/soporte.py por correo. Cerrar la ventana con la «X» llama a `cerrar`, para que no vuelva a abrirse sola.
"""
import streamlit as st

from componentes_plataforma.acceso.sesion import usuario_en_sesion
from componentes_plataforma.legal.contenido import CORREO
from herramientas import soporte

# Claves de st.session_state: ventana abierta y resultado del último envío.
CLAVE_ABIERTO = "soporte_abierto"
CLAVE_RESULTADO = "soporte_resultado"

# Preguntas frecuentes: (pregunta, respuesta).
PREGUNTAS = (
    ("¿El agente puede operar sin mi permiso?",
     "Propone las órdenes y solo se ejecutan cuando tú las confirmas, o si autorizas una vigilancia automática, que opera dentro de los límites de riesgo que defines y que puedes detener cuando quieras."),
    ("¿Es seguro conectar mi cuenta de Capital.com?",
     "Las claves de tu cuenta se guardan cifradas y solo se usan para lo que tú pides o confirmas. Puedes desconectarla cuando quieras."),
    ("¿Cómo cierro sesión en todos mis dispositivos?",
     "Desde Mi perfil, en la sección de seguridad."),
    ("¿Cómo elimino mi cuenta y mis datos?",
     f"Escríbenos a {CORREO} y lo gestionamos."),
)


# TITULO ABRIR Y CERRAR

def abrir() -> None:
    """Callback del botón de soporte: marca la ventana como abierta y olvida el resultado del envío anterior."""
    st.session_state[CLAVE_ABIERTO] = True
    st.session_state.pop(CLAVE_RESULTADO, None)


def cerrar() -> None:
    """Callback al cerrar la ventana con la «X»: la marca como cerrada."""
    st.session_state.pop(CLAVE_ABIERTO, None)


# TITULO FORMULARIO

def _formulario() -> None:
    """Pestaña «Reportar un problema»: tema, mensaje y botón de envío; muestra debajo el resultado del último intento.

    Al enviar guarda el resultado en la sesión y llama a herramientas/soporte.enviar_reporte, que valida, aplica los límites y manda el correo."""
    with st.form("form_soporte", border=False):
        tema = st.selectbox("Tema", soporte.TEMAS)
        mensaje = st.text_area("Qué pasó", placeholder="Describe qué hacías y qué viste en pantalla.", height=130, max_chars=soporte.MAXIMO_CARACTERES)
        st.caption("Adjuntamos solos tu usuario, la sección en que estabas, la hora y tu navegador. Nunca incluimos contraseñas ni claves.")
        enviar = st.form_submit_button("Enviar reporte", type="primary", width="stretch")
    if enviar:
        try:
            navegador = st.context.headers.get("User-Agent", "")
        except Exception:
            navegador = ""
        st.session_state[CLAVE_RESULTADO] = soporte.enviar_reporte(
            usuario_en_sesion() or {}, tema, mensaje, str(st.session_state.get("navegacion_activo", "")), navegador)
    resultado = st.session_state.get(CLAVE_RESULTADO)
    if resultado:
        (st.success if resultado["ok"] else st.error)(resultado["mensaje"])
    st.caption(f"Puedes enviar hasta {soporte.MAXIMO_POR_DIA} reportes al día.")


# TITULO PREGUNTAS FRECUENTES

def _preguntas() -> None:
    """Pestaña «Preguntas frecuentes»: una pregunta por desplegable."""
    for pregunta, respuesta in PREGUNTAS:
        with st.expander(pregunta):
            st.write(respuesta)


# TITULO CONTACTO

def _contacto() -> None:
    """Pestaña «Contacto y documentos»: el correo de la empresa y los enlaces a los documentos legales (se abren en otra pestaña)."""
    st.markdown(f"**Correo**  \n{CORREO}")
    st.markdown("**Documentos**  \n[Términos de uso](?legal=terminos)  \n[Privacidad y cookies](?legal=privacidad)  \n[Aviso de riesgo](?legal=riesgo)")


# TITULO DIALOGO

@st.dialog("Soporte", width="large", on_dismiss=cerrar)
def _dialogo() -> None:
    """Dibuja la ventana con sus tres pestañas."""
    st.caption("Cuéntanos qué pasó y te respondemos por correo.")
    reporte, preguntas, contacto = st.tabs(["Reportar un problema", "Preguntas frecuentes", "Contacto y documentos"])
    with reporte:
        _formulario()
    with preguntas:
        _preguntas()
    with contacto:
        _contacto()
    st.caption("P&J no entrega asesoría financiera.")


# TITULO RENDERIZAR MODAL SOPORTE

def renderizar_modal_soporte() -> None:
    """Llamar desde aplicacion_principal/dialogos.py (fuera de los fragmentos en vivo): abre la ventana solo si está marcada como abierta."""
    if st.session_state.get(CLAVE_ABIERTO):
        _dialogo()


# -------------------------------------------------------------------------------------------------------
# ------------------------------------- FIN Piña y Jara dialogo .PY -------------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
