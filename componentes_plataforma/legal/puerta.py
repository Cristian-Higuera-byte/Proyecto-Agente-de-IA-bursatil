# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# -------------------------------------- INICIO Piña y Jara puerta .PY ----------------------------------
# -------------------------------------------------------------------------------------------------------

"""Puerta de aceptación (V22 de la auditoría): nadie usa la plataforma sin la constancia vigente de los tres documentos legales.

Se llama justo después del inicio de sesión. Consulta en la base de datos si la ÚLTIMA aceptación de cada documento es de la versión vigente (`contenido.VERSION`); si falta, está a medias (por
ejemplo, el alta no pudo guardarla), es de una versión anterior (el texto cambió) o no se puede comprobar, muestra una pantalla para aceptar y detiene la ejecución con `st.stop()`: nada del
panel se dibuja ni se habilita. Al aceptar, las tres filas se guardan de forma atómica y, solo si la base lo confirma, se continúa. El resultado se recuerda en la sesión para no consultar en cada clic.
"""
from html import escape
from pathlib import Path

import streamlit as st

from componentes_plataforma._estaticos import estilos
from componentes_plataforma.legal import contenido
from componentes_plataforma.legal.paginas import casilla_aceptacion
from herramientas import aceptaciones_legales

# Hoja de estilos de la pantalla (mismo aspecto que el inicio de sesión y «Conectar mi cuenta»)
_CSS = Path(__file__).parent / "estilos_puerta.css"

# Clave de st.session_state con (id del usuario, versión) cuya aceptación ya se comprobó en esta sesión.
_CLAVE_OK = "_aceptacion_legal_ok"


# TITULO USUARIO ID

def _usuario_id(usuario: dict):
    """El id numérico del usuario o None si no lo tiene (por ejemplo, el modo local sin cuenta)."""
    try:
        return int((usuario or {}).get("id"))
    except (TypeError, ValueError):
        return None


# TITULO REQUERIR ACEPTACION

def requerir_aceptacion(usuario: dict) -> None:
    """Deja pasar si el usuario tiene vigente la aceptación de los tres documentos; si no, muestra la pantalla de aceptación y detiene la ejecución.

    Recibe el diccionario del usuario autenticado. Sin id numérico no hace nada. Efectos: consulta la base (una vez por sesión y versión) y, al aceptar, escribe las tres filas."""
    uid = _usuario_id(usuario)
    if uid is None:
        return
    if st.session_state.get(_CLAVE_OK) == (uid, contenido.VERSION):
        return
    if aceptaciones_legales.vigentes(uid, aceptaciones_legales.DOCUMENTOS_GENERALES, contenido.VERSION):
        st.session_state[_CLAVE_OK] = (uid, contenido.VERSION)
        return
    st.session_state.pop(_CLAVE_OK, None)
    _pantalla(uid, usuario)
    st.stop()


# TITULO PANTALLA

def _pantalla(uid: int, usuario: dict) -> None:
    """Dibuja la pantalla para aceptar los tres documentos en su versión vigente (con el mismo estilo del inicio de sesión) y guarda la aceptación al confirmar."""
    st.html(estilos(_CSS))
    with st.container(key="puerta_aceptacion"):
        st.html("<div class='pa-cabecera'><div class='pa-logo'>P&amp;J</div>"
                f"<div class='pa-titulo'>Hola, {escape(str((usuario or {}).get('nombre', '')))}</div>"
                f"<div class='pa-sub'>Antes de usar la plataforma necesitamos tu aceptación de los documentos legales en su <b>versión {escape(contenido.VERSION)}</b> "
                f"(vigente desde el {escape(contenido.VIGENTE_DESDE)}). Puede ser porque es tu primera vez, porque actualizamos los textos o porque no quedó la constancia al crear tu cuenta.</div></div>")
        acepto = casilla_aceptacion("puerta_acepto")
        if st.button("Aceptar y continuar", type="primary", width="stretch", key="puerta_continuar"):
            if not acepto:
                st.error("Para continuar debes aceptar los términos de uso, la política de privacidad y el aviso de riesgo.")
            elif aceptaciones_legales.registrar(uid, aceptaciones_legales.DOCUMENTOS_GENERALES, contenido.VERSION):
                st.session_state[_CLAVE_OK] = (uid, contenido.VERSION)
                st.rerun()
            else:
                st.error("No pudimos guardar tu aceptación. No se activó nada: inténtalo de nuevo en un momento.")
    st.html("<p class='pa-pie'>¿No quieres aceptar ahora? <a href='?logout=1' target='_self'>Cerrar sesión</a></p>")


# -------------------------------------------------------------------------------------------------------
# --------------------------------------- FIN Piña y Jara puerta .PY ------------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
