# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# -------------------------------- INICIO Piña y Jara pantallas_correo .PY ------------------------------
# -------------------------------------------------------------------------------------------------------

"""
acceso/pantallas_correo.py
--------------------------
Pantallas del acceso que dependen del correo: «Revisa tu correo» (con reenvío del enlace), confirmación del correo (`?verificar=TOKEN`), «Olvidé mi
contraseña» y elegir una contraseña nueva (`?recuperar=TOKEN`). Las dibuja `requerir_login()` (acceso/pantalla.py); la lógica está en
herramientas/gestor_autenticacion.py.
"""
import streamlit as st

from herramientas.gestor_autenticacion import (
    reenviar_verificacion, restablecer_contrasena, solicitar_recuperacion, verificar_correo)

# Logo "P&J" en HTML en línea (color naranja de la marca).
_LOGO_HTML = (
    "<span style='font-size:40px; font-weight:800; color:#ff6b35; letter-spacing:1px; "
    "font-family:-apple-system,\"Segoe UI\",Roboto,Arial,sans-serif;'>P&amp;J</span>"
)

# Clave de session_state con la cuenta que espera confirmar su correo (id, nombre, email), para poder reenviarle el enlace.
CLAVE_PENDIENTE = "verificacion_pendiente"


# TITULO CABECERA

def cabecera(subtitulo: str) -> None:
    """Dibuja el logo, el título y un subtítulo, centrados, como encabezado de cualquier pantalla de acceso."""
    st.markdown(
        f"<div style='text-align:center; margin-top:8vh;'>{_LOGO_HTML}"
        "<h1 style='margin:10px 0 2px;'>P&amp;J Finance</h1>"
        f"<p style='color:#8b949e; margin:0 0 18px;'>{subtitulo}</p></div>",
        unsafe_allow_html=True,
    )


# TITULO ENLACES

def enlaces_inferiores(*enlaces: str) -> None:
    """Dibuja debajo del formulario los enlaces que se pasan como HTML, uno por línea y centrados."""
    st.markdown("".join(f"<p style='text-align:center; color:#8b949e; margin:6px 0 0;'>{e}</p>" for e in enlaces), unsafe_allow_html=True)


# TITULO REVISA TU CORREO

def vista_revisa_correo() -> bool:
    """Si hay una cuenta esperando confirmar su correo, dibuja «Revisa tu correo» con el botón de reenvío y devuelve True; si no, devuelve False.

    El reenvío usa solo los datos que guardó el servidor en la sesión (nunca una dirección escrita en un formulario), así el botón no sirve para enviar
    correos a terceros. Efecto secundario: puede enviar un correo.
    """
    pendiente = st.session_state.get(CLAVE_PENDIENTE)
    if not pendiente:
        return False
    cabecera("Revisa tu correo")
    st.info(f"Enviamos un enlace de confirmación a **{pendiente['email']}**. Ábrelo para activar tu cuenta; vence en 24 horas. "
            "Si no lo ves, mira la carpeta de spam.")
    if st.button("Reenviar el enlace", width="stretch", key="reenviar_verificacion"):
        resultado = reenviar_verificacion(pendiente["id"], pendiente["nombre"], pendiente["email"])
        (st.success if resultado["ok"] else st.warning)(resultado["mensaje"])
    if st.button("Usar otra cuenta", width="stretch", key="otra_cuenta"):
        del st.session_state[CLAVE_PENDIENTE]
        st.rerun()
    enlaces_inferiores("Cuando lo confirmes, <a href='?acceso=entrar' target='_self'>inicia sesión</a>")
    return True


# TITULO CONFIRMAR CORREO

def vista_verificacion(token: str) -> None:
    """Pantalla del enlace `?verificar=TOKEN`: confirma el correo una sola vez y muestra el resultado.

    Streamlit vuelve a ejecutar la página con cada interacción, y el enlace solo sirve una vez; por eso el resultado se guarda en la sesión del navegador
    y no se vuelve a consultar. Efecto secundario: la primera vez, escribe en la base de datos.
    """
    clave = f"verificacion_resultado_{token}"
    if clave not in st.session_state:
        st.session_state[clave] = verificar_correo(token)
    resultado = st.session_state[clave]
    cabecera("Confirmación de correo")
    if resultado["ok"]:
        st.success(resultado["mensaje"])
    else:
        st.error(resultado["mensaje"])
    enlaces_inferiores("<a href='?acceso=entrar' target='_self'>Ir a iniciar sesión</a>")


# TITULO OLVIDE MI CONTRASENA

def vista_olvide_contrasena() -> None:
    """Formulario «Olvidé mi contraseña»: pide el correo y envía el enlace; responde igual exista o no la cuenta."""
    cabecera("Recupera el acceso a tu cuenta")
    with st.form("form_recordar", border=True):
        correo = st.text_input("Email", key="recordar_correo", placeholder="tucorreo@dominio.com")
        enviar = st.form_submit_button("Enviarme el enlace", width="stretch", type="primary")
    if enviar:
        resultado = solicitar_recuperacion(correo)
        (st.success if resultado["ok"] else st.error)(resultado["mensaje"])
    enlaces_inferiores("<a href='?acceso=entrar' target='_self'>← Volver a iniciar sesión</a>")


# TITULO CONTRASENA NUEVA

def vista_recuperacion(token: str) -> None:
    """Pantalla del enlace `?recuperar=TOKEN`: pide la contraseña nueva dos veces y la guarda.

    El enlace no se gasta al abrir la página sino al guardar una contraseña válida. Efecto secundario: al guardar, escribe en la base de datos.
    """
    cabecera("Elige una contraseña nueva")
    if st.session_state.get("recuperacion_lista"):
        st.success(st.session_state["recuperacion_lista"])
        enlaces_inferiores("<a href='?acceso=entrar' target='_self'>Ir a iniciar sesión</a>")
        return
    with st.form("form_recuperar", border=True):
        nueva = st.text_input("Contraseña nueva", type="password", key="recuperar_nueva", help="Mínimo 8 caracteres, con letras y números")
        repetida = st.text_input("Repite la contraseña", type="password", key="recuperar_repetida")
        guardar = st.form_submit_button("Guardar contraseña", width="stretch", type="primary")
    if guardar:
        if nueva != repetida:
            st.error("Las contraseñas no coinciden.")
        else:
            resultado = restablecer_contrasena(token, nueva)
            if resultado["ok"]:
                st.session_state["recuperacion_lista"] = resultado["mensaje"]
                st.rerun()
            else:
                st.error(resultado["mensaje"])
    enlaces_inferiores("¿El enlace venció? <a href='?acceso=recordar' target='_self'>Pide uno nuevo</a>")


# -------------------------------------------------------------------------------------------------------
# --------------------------------- FIN Piña y Jara pantallas_correo .PY --------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
