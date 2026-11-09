# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ----------------------------------- INICIO Piña y Jara pantalla .PY -----------------------------------
# -------------------------------------------------------------------------------------------------------

"""
acceso/pantalla.py
-----------------
Pantalla de inicio de sesión / registro (UI) conectada a Supabase (tabla `usuarios`).
`requerir_login()` es la puerta de entrada de la app: si no hay sesión, dibuja la portada pública (o el formulario de acceso si llega `?acceso=entrar|crear`)
y DETIENE la ejecución; si la hay, devuelve el dict del usuario. La mecánica de
sesión (iniciar/cerrar/restaurar token) vive en acceso/sesion.py.

Uso en aplicacion.py:
    from componentes_plataforma.acceso import requerir_login
    usuario = requerir_login()   # detiene la app si no hay sesión
    # ... a partir de aquí el usuario está autenticado (dict con id/nombre/email)
"""
from pathlib import Path

import streamlit as st

from componentes_plataforma._estaticos import estilos
from componentes_plataforma.legal import DOCUMENTOS, VERSION, aviso_cookie, casilla_aceptacion, vista_legal
from datetime import date

from componentes_plataforma.perfil import almacen as almacen_perfil
from componentes_plataforma.perfil.datos import nombre_de, opciones
from componentes_plataforma.perfil.validacion import validar_nacimiento
from herramientas import aceptaciones_legales
from herramientas.gestor_autenticacion import autenticar_usuario, registrar_usuario

from .cookie import aplicar_pendiente
from .pantallas_correo import (
    CLAVE_PENDIENTE, CLAVE_REVISA, aviso_sin_verificar, cabecera, enlaces_inferiores, iniciar_espera_reenvio, medidor_contrasena, medidor_en_vivo, pestanas,
    vista_olvide_contrasena, vista_recuperacion, vista_revisa_correo, vista_verificacion)
from .sesion import cerrar_sesion, iniciar_sesion, usuario_en_sesion
from componentes_plataforma.vitrina_planes import html_beneficios, html_pista, html_plan_elegido, html_vitrina, plan_valido

# CSS de las pantallas de acceso (columna centrada y responsiva); se vuelve a leer solo si el archivo cambia en disco.
_CSS = Path(__file__).parent / "estilos.css"


# TITULO PANTALLA CENTRADA

def _centrada(contenido, titulo: str, subtitulo: str) -> None:
    """Dibuja una pantalla de acceso de una sola columna centrada, sin los planes: la cabecera con el logo y una tarjeta con lo que dibuja `contenido`
    (una función sin parámetros), con el mismo estilo del inicio de sesión y el registro. Se usa en «Revisa tu correo» y en el resultado de confirmar el correo."""
    with st.container(key="acceso_centrado"):
        cabecera(titulo, subtitulo)
        with st.container(border=True):
            st.markdown("<span class='acc-tarjeta'></span>", unsafe_allow_html=True)
            contenido()


# TITULO REQUERIR LOGIN

def requerir_login() -> dict:
    """Puerta de entrada de la app: exige que el usuario haya iniciado sesión.

    Si el parámetro de URL `logout=1` está presente, cierra la sesión y limpia la URL. Si hay sesión y llega `perfil=...`, abre la
    vista de perfil (en la sección indicada) y quita el parámetro conservando el token de sesión. Si hay
    sesión (o se restaura desde el token de la URL) devuelve el dict del usuario
    ({id, nombre, email}). Si no, dibuja la pantalla de login/registro centrada y detiene la
    ejecución con `st.stop()`, de modo que nada del dashboard se renderiza sin autenticar.
    Efectos secundarios: lectura/escritura de `st.query_params`, consultas a Supabase vía
    herramientas.gestor_autenticacion y, al autenticar, un `st.rerun()` desde iniciar_sesion.
    """
    # Cerrar sesión vía enlace del menú (?logout=1)
    if st.query_params.get("logout") == "1":
        cerrar_sesion()
        st.query_params.clear()

    # Enlaces que llegan por correo: confirmar el correo (?verificar=TOKEN) o elegir una contraseña nueva (?recuperar=TOKEN). Se atienden antes que el resto
    # y, como son pantallas completas, no dependen de que haya sesión.
    token_verificar = st.query_params.get("verificar")
    token_recuperar = st.query_params.get("recuperar")
    if token_verificar or token_recuperar:
        st.html(estilos(_CSS))
        with st.container():
            if token_verificar:
                _centrada(lambda: vista_verificacion(token_verificar), "Confirmación de correo", "Un último paso para activar tu cuenta")
            else:
                vista_recuperacion(token_recuperar)
        st.stop()

    # Documentos legales (?legal=terminos|privacidad|riesgo): pantalla completa que se puede leer con o sin sesión iniciada
    documento_legal = st.query_params.get("legal")
    if documento_legal in DOCUMENTOS:
        vista_legal(documento_legal, con_sesion=usuario_en_sesion() is not None)
        st.stop()

    # Reutiliza la sesión de la pestaña o la restaurada desde el token de la URL
    usuario = usuario_en_sesion()
    # Escribe o borra en el navegador la cookie de «mantener sesión» que dejó pendiente iniciar_sesion o cerrar_sesion
    aplicar_pendiente()
    if usuario is not None:
        # Enlaces «Mi perfil» / «Configuración» del menú del usuario (?perfil=1 o ?perfil=<sección>): abren la vista de perfil.
        destino = st.query_params.get("perfil")
        if destino:
            st.session_state.navegacion_activo = "perfil"
            if destino != "1":
                st.session_state.perfil_seccion = destino
            del st.query_params["perfil"]
        return usuario

    # --- No autenticado ---
    # Sin `?acceso=` se muestra la portada pública (presentación de la plataforma, con los botones «Iniciar sesión» y «Regístrate»); con `?acceso=entrar` o
    # `?acceso=crear` o `?acceso=recordar` (olvidé mi contraseña), el formulario correspondiente.
    modo = st.query_params.get("acceso")
    if modo not in ("entrar", "crear", "recordar"):
        from componentes_plataforma.portada import renderizar_portada
        renderizar_portada()
        st.stop()
    # Una sola columna centrada, de ancho limitado en el escritorio y completo en el celular (ver acceso/estilos.css)
    st.html(estilos(_CSS))
    with st.container():
        if modo == "recordar":
            vista_olvide_contrasena()
            st.stop()
        # Con una cuenta recién creada esperando confirmar su correo se muestra «Revisa tu correo» en lugar del formulario
        if st.session_state.get(CLAVE_REVISA):
            _centrada(vista_revisa_correo, "Confirma tu correo", "Un último paso para activar tu cuenta")
            st.stop()
        # Pantalla dividida: el formulario a la izquierda (fijo al bajar) y los planes con su detalle a la derecha; en pantallas angostas, uno debajo del otro (acceso/estilos.css)
        with st.container(key="acceso_dividido"):
            izquierda, derecha = st.columns([5, 7], gap="large")
            with izquierda:
                # Cabecera con logo, título y subtítulo, y las pestañas para pasar de un formulario al otro
                if modo == "entrar":
                    cabecera("P&amp;J Finance", "Inicia sesión para acceder al panel bursátil")
                else:
                    cabecera("Crea tu cuenta", "Te enviaremos un enlace para confirmar tu correo")
                # Plan que el usuario escogió en la vitrina de planes (?plan=pro): en el registro se le confirma arriba del formulario y su tarjeta queda marcada abajo
                elegido = plan_valido(st.query_params.get("plan"))
                if modo == "crear" and elegido:
                    st.html(html_plan_elegido(elegido))

                with st.container(border=True):
                    pestanas(modo)

                    # --- Iniciar sesión ---
                    if modo == "entrar":
                        with st.form("form_login", border=False):
                            correo = st.text_input("Correo electrónico", key="inicio_sesion_correo", placeholder="nombre@correo.com")
                            contrasena = st.text_input("Contraseña", type="password", key="inicio_sesion_contrasena")
                            st.markdown("<p style='text-align:right; margin:-6px 0 4px; font-size:13px;'><a href='?acceso=recordar' target='_self'>¿Olvidaste tu contraseña?</a></p>",
                                        unsafe_allow_html=True)
                            enviar = st.form_submit_button("Entrar", width="stretch", type="primary")
                        if enviar:
                            # Valida credenciales; si son correctas inicia sesión (rerun), si el correo no está confirmado ofrece reenviar el enlace, si no muestra el error
                            resultado = autenticar_usuario(correo, contrasena)
                            if resultado["ok"]:
                                iniciar_sesion(resultado["usuario"])
                            elif resultado.get("codigo") == "sin_verificar":
                                st.session_state[CLAVE_PENDIENTE] = resultado["pendiente"]
                            else:
                                st.session_state.pop(CLAVE_PENDIENTE, None)
                                st.error(resultado["mensaje"])
                        aviso_sin_verificar()
                        aviso_cookie()

                    # --- Crear cuenta ---
                    else:
                        with st.form("form_registro", border=False):
                            nombres = st.text_input("Nombres", key="registro_nombres", placeholder="Ana María")
                            apellido_paterno = st.text_input("Apellido paterno", key="registro_apellido_paterno", placeholder="Pérez")
                            apellido_materno = st.text_input("Apellido materno", key="registro_apellido_materno", placeholder="Soto")
                            nacimiento = st.date_input("Fecha de nacimiento", value=None, min_value=date(1900, 1, 1), max_value=date.today(), format="DD/MM/YYYY",
                                                       key="registro_nacimiento", help="Debes ser mayor de 18 años para operar.")
                            genero = st.selectbox("Género (opcional)", [i for i, _ in opciones("generos")], index=None, placeholder="Selecciona…",
                                                  format_func=lambda i: nombre_de("generos", i), key="registro_genero")
                            correo_r = st.text_input("Correo electrónico", key="registro_correo", placeholder="nombre@correo.com")
                            contrasena_r = st.text_input("Contraseña", type="password", key="registro_contrasena")
                            medidor_contrasena("Contraseña")
                            acepto = casilla_aceptacion("registro_acepto")
                            crear = st.form_submit_button("Crear cuenta", width="stretch", type="primary")
                        medidor_en_vivo()
                        if crear and not acepto:
                            st.error("Para crear tu cuenta debes aceptar los términos de uso, la política de privacidad y el aviso de riesgo.")
                        elif crear:
                            # Valida nombres, apellidos y mayoría de edad antes de crear la cuenta; el perfil guarda ambos apellidos por separado y juntos
                            nombres, paterno, materno = (" ".join((x or "").split()) for x in (nombres, apellido_paterno, apellido_materno))
                            apellidos = f"{paterno} {materno}".strip()
                            edad_ok, aviso_edad = validar_nacimiento(nacimiento)
                            if not (nombres and paterno and materno):
                                resultado = {"ok": False, "mensaje": "Completa tus nombres, apellido paterno y apellido materno.", "usuario": None}
                            elif not edad_ok:
                                resultado = {"ok": False, "mensaje": aviso_edad, "usuario": None}
                            else:
                                resultado = registrar_usuario(f"{nombres} {apellidos}", correo_r, contrasena_r)
                            if resultado["ok"]:
                                # Guarda los datos personales en el perfil (si falla, el nombre completo ya quedó en la cuenta)
                                try:
                                    almacen_perfil.guardar(resultado["usuario"]["id"], {"nombres": nombres, "apellidos": apellidos, "apellido_paterno": paterno,
                                                                                         "apellido_materno": materno, "fecha_nacimiento": nacimiento, **({"genero": genero} if genero else {})})
                                except Exception:  # noqa: BLE001
                                    pass
                                # Deja constancia de qué versión de los documentos legales aceptó (si falla, no impide el registro)
                                aceptaciones_legales.registrar(resultado["usuario"]["id"], list(DOCUMENTOS), VERSION)
                            if not resultado["ok"]:
                                st.error(resultado["mensaje"])
                            elif resultado.get("requiere_verificacion"):
                                # Con verificación activa no se inicia sesión: primero debe confirmar su correo
                                st.session_state[CLAVE_REVISA] = resultado["usuario"]
                                iniciar_espera_reenvio()
                                st.rerun()
                            else:
                                # Inicia sesión automáticamente tras registrarse
                                iniciar_sesion(resultado["usuario"])

                # Enlace hacia la vitrina de planes (solo se ve cuando la pantalla es angosta y los planes quedan debajo) y enlace para volver a la portada
                st.html(html_beneficios())
                st.html(html_pista())
                enlaces_inferiores("<a href='./' target='_self'>← Volver a la portada</a>")
            with derecha:
                st.html(html_vitrina(elegido))

    # Corta la ejecución para que no se pinte el resto de la app
    st.stop()
    return {}  # (nunca se alcanza)


# -------------------------------------------------------------------------------------------------------
# ------------------------------------- FIN Piña y Jara pantalla .PY ------------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
