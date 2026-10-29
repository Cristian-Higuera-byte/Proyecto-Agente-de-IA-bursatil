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
Piezas visuales y pantallas del acceso: cabecera, pestañas «Iniciar sesión / Crear cuenta», aviso de correo sin verificar, medidor de fuerza de la
contraseña, «Revisa tu correo» (con reenvío y espera), confirmación del correo (`?verificar=TOKEN`), «Olvidé mi contraseña» y contraseña nueva
(`?recuperar=TOKEN`). Las dibuja `requerir_login()` (acceso/pantalla.py); la lógica está en herramientas/gestor_autenticacion.py y la regla de las
contraseñas en herramientas/contrasenas.py. El diseño sigue la maqueta aprobada: tarjetas oscuras, íconos en círculo y el rojo de la marca en los botones.
"""
import time

import streamlit as st

from herramientas import contrasenas
from herramientas.gestor_autenticacion import (
    reenviar_verificacion, restablecer_contrasena, solicitar_recuperacion, verificar_correo)

# Logo "P&J" en HTML en línea (color naranja de la marca).
_LOGO_HTML = (
    "<span style='font-size:40px; font-weight:800; color:#ff6b35; letter-spacing:1px; "
    "font-family:-apple-system,\"Segoe UI\",Roboto,Arial,sans-serif;'>P&amp;J</span>"
)

# Claves de session_state: cuenta recién creada que debe confirmar su correo (pantalla «Revisa tu correo»), cuenta que intentó entrar sin haberlo
# confirmado (aviso en el inicio de sesión), hora desde la que se puede reenviar el enlace y mensaje del último reenvío.
CLAVE_REVISA = "verificacion_revisa"
CLAVE_PENDIENTE = "verificacion_pendiente"
CLAVE_ENFRIAMIENTO = "reenvio_disponible_desde"
CLAVE_MENSAJE = "reenvio_mensaje"
CLAVE_CONTANDO = "reenvio_contando"

# Segundos entre un envío y el siguiente (el servidor exige 60).
SEGUNDOS_REENVIO = 60

# Colores de los íconos en círculo y de los avisos: (fondo, trazo).
_COLORES = {"azul": ("#0d2a4a", "#58a6ff"), "verde": ("#0f2d1a", "#3fb950"), "ambar": ("#2d1f10", "#e3b341"), "rojo": ("#3a1618", "#ff7b72")}

# Íconos SVG en línea (trazo con el color del texto).
_ENVOLTURA_SVG = "<svg width='22' height='22' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>{}</svg>"
_ICONOS = {
    "correo": _ENVOLTURA_SVG.format("<rect x='3' y='5' width='18' height='14' rx='2'/><polyline points='3,7 12,13 21,7'/>"),
    "ok": _ENVOLTURA_SVG.format("<polyline points='5,13 10,18 19,7'/>"),
    "error": _ENVOLTURA_SVG.format("<line x1='6' y1='6' x2='18' y2='18'/><line x1='18' y1='6' x2='6' y2='18'/>"),
}

# Colores de las 4 barras del medidor según cuántas se llenan.
_COLORES_BARRAS = {1: "#f85149", 2: "#db6d28", 3: "#e3b341", 4: "#3fb950"}


# TITULO CABECERA

def cabecera(titulo: str, subtitulo: str) -> None:
    """Dibuja el logo, el título y un subtítulo, centrados, como encabezado de cualquier pantalla de acceso."""
    st.markdown(
        f"<div style='text-align:center;'>{_LOGO_HTML}"
        f"<h2 style='margin:8px 0 2px; font-size:22px;'>{titulo}</h2>"
        f"<p style='color:#8b949e; margin:0 0 14px; font-size:14px;'>{subtitulo}</p></div>",
        unsafe_allow_html=True,
    )


# TITULO PESTANAS

def pestanas(activa: str) -> None:
    """Dibuja las pestañas «Iniciar sesión» y «Crear cuenta» (enlaces a ?acceso=entrar y ?acceso=crear); `activa` es «entrar» o «crear»."""
    def una(destino: str, texto: str) -> str:
        if destino == activa:
            estilo = "color:#ff4b4b; border-bottom:2px solid #ff4b4b; font-weight:600;"
        else:
            estilo = "color:#8b949e; border-bottom:2px solid transparent;"
        return f"<a href='?acceso={destino}' target='_self' style='{estilo} padding:0 4px 8px; text-decoration:none; font-size:14px;'>{texto}</a>"
    st.markdown(f"<div style='display:flex; gap:20px; justify-content:center; border-bottom:1px solid #30363d; margin:0 0 14px;'>"
                f"{una('entrar', 'Iniciar sesión')}{una('crear', 'Crear cuenta')}</div>", unsafe_allow_html=True)


# TITULO ENLACES

def enlaces_inferiores(*enlaces: str) -> None:
    """Dibuja debajo de la tarjeta los enlaces que se pasan como HTML, uno por línea y centrados."""
    st.markdown("".join(f"<p style='text-align:center; color:#8b949e; margin:6px 0 0; font-size:14px;'>{e}</p>" for e in enlaces), unsafe_allow_html=True)


# TITULO AVISO

def aviso(html: str, color: str = "ambar") -> None:
    """Dibuja un aviso en recuadro (por defecto ámbar) con el HTML dado."""
    fondo, trazo = _COLORES[color]
    st.markdown(f"<div style='background:{fondo}; border:1px solid {trazo}55; border-radius:8px; padding:8px 12px; color:{trazo}; font-size:13px;'>{html}</div>",
                unsafe_allow_html=True)


# TITULO ICONO EN CIRCULO

def icono_circular(nombre: str, color: str) -> None:
    """Dibuja un ícono (correo, ok o error) dentro de un círculo de color, centrado."""
    fondo, trazo = _COLORES[color]
    st.markdown(f"<div style='width:48px; height:48px; border-radius:50%; margin:10px auto 8px; background:{fondo}; color:{trazo}; display:flex; "
                f"align-items:center; justify-content:center;'>{_ICONOS[nombre]}</div>", unsafe_allow_html=True)


# TITULO MEDIDOR

def medidor_contrasena(contrasena: str) -> None:
    """Dibuja bajo el campo de contraseña las 4 barras de fuerza y la lista de requisitos, marcando los que ya se cumplen."""
    llenas = contrasenas.barras(contrasena)
    barras = "".join(f"<span style='flex:1; height:4px; border-radius:2px; background:{_COLORES_BARRAS[llenas] if i < llenas else '#30363d'};'></span>"
                     for i in range(4))
    if not contrasena:
        detalle = f"<p style='color:#8b949e; font-size:12px; margin:4px 0 0;'>{contrasenas.TEXTO_AYUDA}</p>"
    else:
        puntos = "".join(
            f"<span style='color:{'#3fb950' if cumple else '#8b949e'}; font-size:12px; margin-right:12px; white-space:nowrap;'>{'✓' if cumple else '○'} {texto}</span>"
            for texto, cumple in contrasenas.evaluar(contrasena))
        comun = "<p style='color:#f85149; font-size:12px; margin:4px 0 0;'>Esa contraseña es demasiado común.</p>" if contrasenas.es_comun(contrasena) else ""
        detalle = f"<div style='margin-top:4px; line-height:1.7;'>{puntos}</div>{comun}"
    st.markdown(f"<div style='display:flex; gap:4px; margin-top:2px;'>{barras}</div>{detalle}", unsafe_allow_html=True)


# TITULO REENVIAR ENLACE

def _zona_reenvio(cuenta: dict) -> None:
    """Botón «Reenviar enlace» con espera: tras cada envío queda desactivado SEGUNDOS_REENVIO segundos, con la cuenta atrás en pantalla.

    Se ejecuta como fragmento que se refresca solo cada segundo mientras dura la espera. Efecto secundario: al pulsar, envía un correo."""
    restante = int(st.session_state.get(CLAVE_ENFRIAMIENTO, 0) - time.time() + 0.999)
    if restante <= 0 and st.session_state.pop(CLAVE_CONTANDO, False):
        st.rerun()
    if st.button("Reenviar enlace", width="stretch", disabled=restante > 0, key="reenviar_verificacion"):
        resultado = reenviar_verificacion(cuenta["id"], cuenta["nombre"], cuenta["email"])
        st.session_state[CLAVE_MENSAJE] = ("ok" if resultado["ok"] else "aviso", resultado["mensaje"])
        if resultado["ok"]:
            st.session_state[CLAVE_ENFRIAMIENTO] = time.time() + SEGUNDOS_REENVIO
            st.session_state[CLAVE_CONTANDO] = True
        st.rerun()
    mensaje = st.session_state.get(CLAVE_MENSAJE)
    if restante > 0:
        st.caption(f"Puedes reenviarlo en {restante} s")
    elif mensaje:
        (st.success if mensaje[0] == "ok" else st.warning)(mensaje[1])
    else:
        st.caption("¿No llega? Revisa la carpeta de spam.")


# TITULO REVISA TU CORREO

def iniciar_espera_reenvio() -> None:
    """Marca que se acaba de enviar un enlace, para que el botón de reenvío espere antes de poder usarse (el servidor limita un envío por minuto)."""
    st.session_state[CLAVE_ENFRIAMIENTO] = time.time() + SEGUNDOS_REENVIO
    st.session_state[CLAVE_CONTANDO] = True
    st.session_state.pop(CLAVE_MENSAJE, None)


def vista_revisa_correo() -> bool:
    """Si hay una cuenta recién creada esperando confirmar su correo, dibuja «Revisa tu correo» y devuelve True; si no, devuelve False.

    El reenvío usa solo los datos que guardó el servidor en la sesión (nunca una dirección escrita en un formulario), así el botón no sirve para enviar
    correos a terceros."""
    cuenta = st.session_state.get(CLAVE_REVISA)
    if not cuenta:
        return False
    icono_circular("correo", "azul")
    st.markdown(f"<div style='text-align:center;'><h2 style='margin:0; font-size:22px;'>Revisa tu correo</h2>"
                f"<p style='color:#8b949e; margin:6px 0 14px; font-size:14px;'>Enviamos un enlace a <b style='color:#e6edf3'>{cuenta['email']}</b>. "
                "Vence en 24 horas.</p></div>", unsafe_allow_html=True)
    activo = st.session_state.get(CLAVE_ENFRIAMIENTO, 0) > time.time()
    st.fragment(run_every=1 if activo else None)(_zona_reenvio)(cuenta)
    if st.button("Usar otro correo", type="tertiary", width="stretch", key="otra_cuenta"):
        for clave in (CLAVE_REVISA, CLAVE_ENFRIAMIENTO, CLAVE_MENSAJE, CLAVE_CONTANDO):
            st.session_state.pop(clave, None)
        st.query_params["acceso"] = "crear"
        st.rerun()
    enlaces_inferiores("Cuando lo confirmes, <a href='?acceso=entrar' target='_self'>inicia sesión</a>")
    return True


# TITULO AVISO SIN VERIFICAR

def aviso_sin_verificar() -> None:
    """En el inicio de sesión, si la cuenta no ha confirmado su correo, muestra el aviso ámbar y el botón para reenviar el enlace."""
    cuenta = st.session_state.get(CLAVE_PENDIENTE)
    if not cuenta:
        return
    aviso(f"✉ Tu correo aún no está verificado. Revisa <b>{cuenta['email']}</b> o pide otro enlace.")
    if st.button("Reenviar enlace", key="reenviar_desde_login", width="stretch"):
        resultado = reenviar_verificacion(cuenta["id"], cuenta["nombre"], cuenta["email"])
        (st.success if resultado["ok"] else st.warning)(resultado["mensaje"])


# TITULO CONFIRMAR CORREO

def vista_verificacion(token: str) -> None:
    """Pantalla del enlace `?verificar=TOKEN`: confirma el correo una sola vez y muestra el resultado.

    Streamlit vuelve a ejecutar la página con cada interacción, y el enlace solo sirve una vez; por eso el resultado se guarda en la sesión del navegador
    y no se vuelve a consultar. Efecto secundario: la primera vez, escribe en la base de datos."""
    clave = f"verificacion_resultado_{token}"
    if clave not in st.session_state:
        st.session_state[clave] = verificar_correo(token)
    resultado = st.session_state[clave]
    if resultado["ok"]:
        icono_circular("ok", "verde")
        titulo, texto = "Correo confirmado", "Tu cuenta ya está activa. Inicia sesión para continuar."
    else:
        icono_circular("error", "rojo")
        titulo, texto = "No pudimos confirmar tu correo", resultado["mensaje"]
    st.markdown(f"<div style='text-align:center;'><h2 style='margin:0; font-size:22px;'>{titulo}</h2>"
                f"<p style='color:#8b949e; margin:6px 0 14px; font-size:14px;'>{texto}</p></div>", unsafe_allow_html=True)
    st.link_button("Iniciar sesión" if resultado["ok"] else "Ir a iniciar sesión", "?acceso=entrar", type="primary", width="stretch")


# TITULO OLVIDE MI CONTRASENA

def vista_olvide_contrasena() -> None:
    """Formulario «Olvidé mi contraseña»: pide el correo y envía el enlace; responde igual exista o no la cuenta."""
    cabecera("Recupera tu cuenta", "Te enviaremos un enlace para elegir una contraseña nueva")
    with st.form("form_recordar", border=True):
        correo = st.text_input("Correo electrónico", key="recordar_correo", placeholder="nombre@correo.com")
        enviar = st.form_submit_button("Enviarme el enlace", width="stretch", type="primary")
    if enviar:
        resultado = solicitar_recuperacion(correo)
        (st.success if resultado["ok"] else st.error)(resultado["mensaje"])
    enlaces_inferiores("<a href='?acceso=entrar' target='_self'>← Volver a iniciar sesión</a>")


# TITULO CONTRASENA NUEVA

def vista_recuperacion(token: str) -> None:
    """Pantalla del enlace `?recuperar=TOKEN`: pide la contraseña nueva dos veces (con medidor de fuerza) y la guarda.

    El enlace no se gasta al abrir la página sino al guardar una contraseña válida. Efecto secundario: al guardar, escribe en la base de datos."""
    if st.session_state.get("recuperacion_lista"):
        icono_circular("ok", "verde")
        st.markdown(f"<div style='text-align:center;'><h2 style='margin:0; font-size:22px;'>Contraseña actualizada</h2>"
                    f"<p style='color:#8b949e; margin:6px 0 14px; font-size:14px;'>{st.session_state['recuperacion_lista']}</p></div>", unsafe_allow_html=True)
        st.link_button("Ir a iniciar sesión", "?acceso=entrar", type="primary", width="stretch")
        return
    cabecera("Elige una contraseña nueva", "Será la que uses desde ahora para entrar")
    with st.container(border=True):
        nueva = st.text_input("Contraseña nueva", type="password", key="recuperar_nueva")
        medidor_contrasena(nueva)
        repetida = st.text_input("Repite la contraseña", type="password", key="recuperar_repetida")
        guardar = st.button("Guardar contraseña", width="stretch", type="primary", key="recuperar_guardar")
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
