# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ------------------------------------ INICIO Piña y Jara google .PY ------------------------------------
# -------------------------------------------------------------------------------------------------------

"""
acceso/google.py
----------------
«Continuar con Google» en el inicio de sesión y el registro, con el inicio de sesión OpenID Connect que trae Streamlit (`st.login`).

Cómo funciona:
1. El botón llama a `st.login("google")`; Google autentica a la persona y vuelve a `/oauth2callback` (la URI registrada en Google Cloud).
2. Al volver, `atender_retorno()` (que `requerir_login` llama antes de dibujar nada) copia los datos que entregó Google a `st.session_state` y cierra la identidad de
   Streamlit con `st.logout()`: así la sesión de la plataforma sigue siendo SOLO la propia (token `?s=` y cookie de «mantener sesión») y cerrar sesión en la plataforma
   no deja a la persona entrando sola de nuevo.
3. Si el correo ya tiene cuenta, se inicia sesión. Si no, se pide lo que Google no entrega (nombres, apellidos, fecha de nacimiento 18+ y aceptar los documentos legales)
   y se crea la cuenta sin contraseña propia (ver `gestor_autenticacion.registrar_con_google`).

Se activa solo si hay un bloque `[auth]` con el proveedor `google` en `.streamlit/secrets.toml` y está instalada la librería Authlib; si no, no se dibuja nada y la
plataforma funciona como antes. Configuración (el archivo no va a git):

    [auth]
    redirect_uri = "https://pyj.rmcabogados.cl/oauth2callback"
    cookie_secret = "<texto aleatorio largo>"
    [auth.google]
    client_id = "<ID de cliente>"
    client_secret = "<secreto del cliente>"
    server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
"""
from datetime import date

import streamlit as st

from componentes_plataforma._estaticos import estilos
from componentes_plataforma.legal import DOCUMENTOS, VERSION, casilla_aceptacion
from componentes_plataforma.perfil import almacen as almacen_perfil
from componentes_plataforma.perfil.datos import nombre_de, opciones
from componentes_plataforma.perfil.validacion import validar_nacimiento
from herramientas import aceptaciones_legales
from herramientas import limites_formularios as limites
from herramientas.gestor_autenticacion import acceso_con_google, registrar_con_google

from .pantallas_correo import cabecera
from .sesion import iniciar_sesion

# Clave de session_state con los datos que entregó Google mientras se resuelve el ingreso
CLAVE_GOOGLE = "_google_identidad"

_MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")


# TITULO DISPONIBLE

def disponible() -> bool:
    """True si el inicio de sesión con Google está configurado (bloque [auth] con `google` en secrets.toml) y Authlib está instalada."""
    try:
        from streamlit.auth_util import is_authlib_installed
        return bool(is_authlib_installed() and st.secrets["auth"]["google"]["client_id"] and st.secrets["auth"]["google"]["client_secret"])
    except Exception:  # noqa: BLE001 - sin archivo de secretos o sin la clave: Google no está configurado
        return False


# TITULO BOTON

def boton(clave: str) -> None:
    """Dibuja, bajo el formulario, el separador «o» y el botón «Continuar con Google»; al pulsarlo se va a la pantalla de Google. `clave` distingue el botón del login y del registro."""
    if not disponible():
        return
    st.markdown("<div class='acc-separador'><span>o</span></div>", unsafe_allow_html=True)
    if st.button("Continuar con Google", key=clave, width="stretch"):
        st.login("google")


# TITULO DATOS DE GOOGLE

def _datos_de_google() -> dict | None:
    """Lee la identidad que dejó Google (nombre, correo y si el correo está verificado), o None si no hay una sesión de Google en curso."""
    try:
        if not st.user.get("is_logged_in", False):
            return None
        return {"email": (st.user.get("email") or "").strip().lower(), "verificado": bool(st.user.get("email_verified")),
                "nombres": (st.user.get("given_name") or "").strip(), "apellidos": (st.user.get("family_name") or "").strip(),
                "nombre": (st.user.get("name") or "").strip()}
    except Exception:  # noqa: BLE001 - si Streamlit no puede leer la identidad se trata como «sin Google»
        return None


# TITULO ATENDER RETORNO

def atender_retorno(css) -> None:
    """Resuelve el ingreso con Google si hay uno en curso; no hace nada si no lo hay.

    Primero guarda la identidad que entregó Google y cierra la de Streamlit (`st.logout()` reejecuta la página). Después, con la identidad guardada: si el correo no está
    verificado lo rechaza; si ya tiene cuenta inicia sesión; si es nuevo muestra la pantalla para completar los datos y detiene la ejecución."""
    if not disponible():
        return
    datos = _datos_de_google()
    if datos is not None:
        st.session_state[CLAVE_GOOGLE] = datos
        st.logout()
        st.stop()
    datos = st.session_state.get(CLAVE_GOOGLE)
    if not datos:
        return
    st.html(estilos(css))
    if not datos["verificado"] or not datos["email"]:
        st.session_state.pop(CLAVE_GOOGLE, None)
        _pantalla_error("Google no confirmó tu correo, así que no podemos usarlo para entrar. Prueba con otro correo o crea la cuenta con tu correo y contraseña.")
        return
    resultado = acceso_con_google(datos["email"])
    if resultado["ok"]:
        st.session_state.pop(CLAVE_GOOGLE, None)
        iniciar_sesion(resultado["usuario"])
        return
    if resultado.get("codigo") != "nuevo":
        st.session_state.pop(CLAVE_GOOGLE, None)
        _pantalla_error(resultado.get("mensaje", "No pudimos completar el ingreso con Google."))
        return
    _pantalla_completar(datos)
    st.stop()


# TITULO PANTALLA ERROR

def _pantalla_error(mensaje: str) -> None:
    """Pantalla centrada con el motivo por el que no se pudo entrar con Google y el enlace para volver al inicio de sesión."""
    with st.container(key="acceso_centrado"):
        cabecera("No pudimos entrar con Google", "Tu cuenta de Google no se pudo usar")
        with st.container(border=True):
            st.error(mensaje)
            st.markdown("<p style='text-align:center; margin:8px 0 0;'><a href='?acceso=entrar' target='_self'>Volver a iniciar sesión</a></p>", unsafe_allow_html=True)
    st.stop()


# TITULO PANTALLA COMPLETAR

def _pantalla_completar(datos: dict) -> None:
    """Pantalla para quien entra con Google por primera vez: pide lo que Google no entrega (apellidos por separado, fecha de nacimiento 18+, género opcional)
    y la aceptación de los documentos legales. Al enviar crea la cuenta (con el correo ya verificado por Google) y la deja con la sesión iniciada."""
    partes = datos["apellidos"].split(None, 1)
    with st.container(key="acceso_centrado"):
        cabecera("Un último paso", f"Completa tus datos para crear tu cuenta con {datos['email']}")
        with st.container(border=True):
            st.markdown("<span class='acc-tarjeta'></span>", unsafe_allow_html=True)
            with st.form("form_google_completar", border=False):
                nombres = st.text_input("Nombres", value=datos["nombres"], key="google_nombres", max_chars=limites.NOMBRES)
                paterno = st.text_input("Apellido paterno", value=partes[0] if partes else "", key="google_paterno", max_chars=limites.APELLIDO)
                materno = st.text_input("Apellido materno", value=partes[1] if len(partes) > 1 else "", key="google_materno", max_chars=limites.APELLIDO)
                st.markdown("<div class='acc-etiqueta'>Fecha de nacimiento</div>", unsafe_allow_html=True)
                col_dia, col_mes, col_anio = st.columns([1, 1.6, 1.2], gap="small")
                dia = col_dia.selectbox("Día", list(range(1, 32)), index=None, placeholder="Día", key="google_dia", label_visibility="collapsed")
                mes = col_mes.selectbox("Mes", list(range(1, 13)), index=None, placeholder="Mes", key="google_mes", label_visibility="collapsed", format_func=lambda m: _MESES[m - 1])
                anio = col_anio.selectbox("Año", list(range(date.today().year, 1919, -1)), index=None, placeholder="Año", key="google_anio", label_visibility="collapsed")
                st.caption("Debes ser mayor de 18 años para operar.")
                genero = st.selectbox("Género (opcional)", [i for i, _ in opciones("generos")], index=None, placeholder="Selecciona…",
                                      format_func=lambda i: nombre_de("generos", i), key="google_genero")
                acepto = casilla_aceptacion("google_acepto")
                crear = st.form_submit_button("Crear cuenta", width="stretch", type="primary")
            if crear:
                nombres, paterno, materno = (" ".join((x or "").split()) for x in (nombres, paterno, materno))
                try:
                    nacimiento = date(anio, mes, dia) if (dia and mes and anio) else None
                except ValueError:
                    nacimiento = date.max          # el día no existe en ese mes: validar_nacimiento lo rechaza
                edad_ok, aviso_edad = validar_nacimiento(nacimiento)
                if not (nombres and paterno and materno):
                    st.error("Completa tus nombres, apellido paterno y apellido materno.")
                elif not edad_ok:
                    st.error(aviso_edad)
                elif not acepto:
                    st.error("Para crear tu cuenta debes aceptar los términos de uso, la política de privacidad y el aviso de riesgo.")
                else:
                    apellidos = f"{paterno} {materno}".strip()
                    resultado = registrar_con_google(f"{nombres} {apellidos}", datos["email"])
                    if not resultado["ok"]:
                        st.error(resultado["mensaje"])
                    else:
                        usuario = resultado["usuario"]
                        try:
                            almacen_perfil.guardar(usuario["id"], {"nombres": nombres, "apellidos": apellidos, "apellido_paterno": paterno, "apellido_materno": materno,
                                                                   "fecha_nacimiento": nacimiento, **({"genero": genero} if genero else {})})
                        except Exception:  # noqa: BLE001 - si falla, el nombre completo ya quedó en la cuenta
                            pass
                        aceptaciones_legales.registrar(usuario["id"], list(DOCUMENTOS), VERSION)
                        st.session_state.pop(CLAVE_GOOGLE, None)
                        iniciar_sesion(usuario)
            if st.button("Cancelar", key="google_cancelar", width="stretch"):
                st.session_state.pop(CLAVE_GOOGLE, None)
                st.rerun()


# -------------------------------------------------------------------------------------------------------
# ------------------------------------- FIN Piña y Jara google .PY --------------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
