# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ----------------------------------- INICIO Piña y Jara formulario .PY ---------------------------------
# -------------------------------------------------------------------------------------------------------

"""Protección con reCAPTCHA de un formulario de la plataforma: el componente del navegador y la comprobación al enviar.

Uso en un formulario (los dos pasos van con el mismo nombre de formulario, por ejemplo «login»):
    with st.form("form_login"):
        ...campos...
        dibujar("login")                      # dentro del formulario, antes del botón de enviar
        enviar = st.form_submit_button("Entrar")
    if enviar:
        exigir("login")                       # si no pasa la verificación, avisa, pide el casillero de v2 si hace falta y repite la pantalla
        ...el resto del envío...

Si las claves de reCAPTCHA no están en el .env, ambas funciones no hacen nada (desarrollo).
"""
from pathlib import Path
from typing import Optional

import streamlit as st

import configuracion
from componentes_plataforma._estaticos import texto
from herramientas import recaptcha as verificador

# Carpeta con el script y los estilos del componente.
_ESTATICO = Path(__file__).parent / "estatico"

# El componente se declara una sola vez al importar el módulo (no dentro de las funciones, para no registrarlo dos veces).
_COMPONENTE = st.components.v2.component(
    "pj_recaptcha",
    html="<div class='pj-rc-v2'></div>",
    css=texto(_ESTATICO / "recaptcha.css") + "\n",
    js=texto(_ESTATICO / "recaptcha.js") + "\n",
    isolate_styles=False,
)

# Aviso legal que Google exige cuando se oculta su insignia.
_AVISO_GOOGLE = ("Este sitio está protegido por reCAPTCHA y se aplican la <a href='https://policies.google.com/privacy' target='_blank' rel='noopener'>Política de privacidad</a> "
                 "y los <a href='https://policies.google.com/terms' target='_blank' rel='noopener'>Términos del servicio</a> de Google.")


# TITULO CLAVES

def _clave(formulario: str, parte: str) -> str:
    """Nombre, dentro de `st.session_state`, de una pieza del estado de reCAPTCHA de un formulario (`parte` es «msg», «v2» o «n»)."""
    return f"rc_{parte}_{formulario}"


# TITULO IP

def _ip() -> Optional[str]:
    """Dirección de la persona que envía el formulario, tomada del encabezado X-Forwarded-For del servidor intermedio; None si no se puede saber."""
    try:
        primera = (st.context.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    except Exception:  # noqa: BLE001 - sin contexto de petición (pruebas)
        return None
    return primera or None


# TITULO DIBUJAR

def dibujar(formulario: str) -> None:
    """Pone el componente de reCAPTCHA del formulario `formulario` (sin altura mientras no se pida el casillero) y el aviso legal de Google.

    Muestra también el motivo del último rechazo, si lo hubo. Va dentro del formulario, antes del botón de enviar; sin claves configuradas no dibuja nada."""
    if not verificador.activo():
        return
    mensaje = st.session_state.pop(_clave(formulario, "msg"), None)
    if mensaje:
        st.error(mensaje)
    _COMPONENTE(
        key=f"rc_{formulario}",
        data={
            "v3": configuracion.RECAPTCHA_V3_SITIO,
            "v2": configuracion.RECAPTCHA_V2_SITIO,
            "accion": formulario,
            "pedirV2": bool(st.session_state.get(_clave(formulario, "v2"))),
            "nonce": int(st.session_state.get(_clave(formulario, "n"), 0)),
        },
        on_v3_change=lambda: None,
        on_v2_change=lambda: None,
    )
    st.markdown(f"<div style='font-size:11.5px; color:#6e7681; line-height:1.4; margin:2px 0 6px;'>{_AVISO_GOOGLE}</div>", unsafe_allow_html=True)


# TITULO EXIGIR

def exigir(formulario: str) -> None:
    """Comprueba en el servidor que el envío del formulario `formulario` pasó reCAPTCHA; si no pasó, avisa y repite la pantalla (`st.rerun()`), de modo que el código que sigue no se ejecuta.

    Usa el token de v3 y, si lo hay, el del casillero de v2 que guardó el componente. Un token solo sirve una vez: se sube el contador para que el navegador pida otro. Si v3 puntúa
    bajo, falta o es inválido, se activa el casillero de v2 en la próxima pasada. Sin claves configuradas no hace nada."""
    if not verificador.activo():
        return
    estado = st.session_state.get(f"rc_{formulario}") or {}
    veredicto = verificador.verificar(formulario, str(estado.get("v3") or ""), str(estado.get("v2") or ""), _ip())
    st.session_state[_clave(formulario, "n")] = int(st.session_state.get(_clave(formulario, "n"), 0)) + 1
    if veredicto.ok:
        st.session_state.pop(_clave(formulario, "v2"), None)
        return
    if veredicto.pedir_v2:
        st.session_state[_clave(formulario, "v2")] = True
    st.session_state[_clave(formulario, "msg")] = veredicto.mensaje
    st.rerun()


# -------------------------------------------------------------------------------------------------------
# ------------------------------------ FIN Piña y Jara formulario .PY -----------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
