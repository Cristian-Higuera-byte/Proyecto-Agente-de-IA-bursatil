# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ------------------------------------- INICIO Piña y Jara cookie .PY -----------------------------------
# -------------------------------------------------------------------------------------------------------

"""
acceso/cookie.py
----------------
Escribe y borra en el navegador la cookie de «mantener sesión iniciada». Streamlit puede LEER las cookies del navegador (`st.context.cookies`, también las HttpOnly) pero no
crearlas. Hay dos caminos:

* Con `SERVIDOR_SECRETO` configurado (producción): la cookie la emite el SERVIDOR DE DATOS con HttpOnly, Secure y SameSite=Lax (V06 y V07). Streamlit le da al navegador un boleto de un
  solo uso (herramientas/boleto_sesion.py), un script de altura 0 lo canjea con `POST <servidor>/t/sesion` y, al terminar, recarga la página para que ya cargue con la cookie. Esa
  cookie es la única credencial: la reconoce Streamlit y también el servidor de datos. Las sesiones que quedaron con la cookie antigua (escrita por JavaScript, visible a cualquier
  script) se pasan solas al formato nuevo una vez por pestaña.
* Sin secreto (desarrollo local): la cookie la escribe un script con `document.cookie`, como antes.

La acción se deja pendiente en `st.session_state` (porque al iniciar o cerrar sesión la app se vuelve a ejecutar enseguida) y `aplicar_pendiente()` la emite en la siguiente pasada de `requerir_login()`.
"""
import json
import os

import streamlit as st
import streamlit.components.v1 as components

from herramientas import boleto_sesion
from herramientas.sesion_persistente import DIAS_DURACION, NOMBRE_COOKIE

# Clave de st.session_state donde queda la acción pendiente: ("guardar", token) o ("borrar", None).
_PENDIENTE = "_cookie_sesion_pendiente"
# Clave de st.session_state que recuerda que ya se revisó si la cookie de esta pestaña es la antigua
_REVISADA = "_cookie_sesion_revisada"


# TITULO PROGRAMAR GUARDADO

def programar_guardado(token: str) -> None:
    """Deja pendiente guardar la cookie con ese token en el navegador (se escribe en la próxima pasada de la app)."""
    st.session_state[_PENDIENTE] = ("guardar", token)


# TITULO PROGRAMAR BORRADO

def programar_borrado() -> None:
    """Deja pendiente borrar la cookie del navegador (cerrar sesión)."""
    st.session_state[_PENDIENTE] = ("borrar", None)


# TITULO LEER

def leer() -> str:
    """Devuelve el token de la cookie que el navegador envió en esta petición, o una cadena vacía si no hay."""
    try:
        return st.context.cookies.get(NOMBRE_COOKIE, "") or ""
    except Exception:
        return ""


# TITULO DIRECCION DEL SERVIDOR

def _servidor() -> str:
    """Dirección base del servidor de datos que usa el navegador (la misma variable que el gráfico y los precios en vivo)."""
    return os.environ.get("MT5_API_URL", "http://localhost:8000").rstrip("/")


# TITULO SCRIPT

def _script(accion: str, token: str) -> str:
    """Código JavaScript (de altura 0) que guarda, migra o borra la cookie desde el navegador; `accion` es «guardar», «migrar» o «borrar».

    Con boleto (servidor de datos): guardar canjea el boleto y recarga la página; migrar lo hace solo si el navegador ve la cookie antigua (la HttpOnly no es visible a los scripts) y
    una sola vez por pestaña; borrar le pide al servidor que la borre. Si el servidor no responde, guardar escribe la cookie antigua para no dejar a la persona sin sesión persistente."""
    nombre, valor, duracion, api = json.dumps(NOMBRE_COOKIE), json.dumps(token), DIAS_DURACION * 24 * 3600, json.dumps(_servidor())
    boleto = json.dumps(boleto_sesion.emitir(token)) if accion != "borrar" else '""'
    cabecera = ("var P;try{P=window.parent;}catch(e){return;}var D=P.document;"
                "var seguro=(P.location.protocol==='https:')?'; Secure':'';"
                f"var N={nombre},T={valor},API={api},B={boleto};"
                "function antigua(){D.cookie=N+'='+T+'; Max-Age=" + str(duracion) + "; Path=/; SameSite=Lax'+seguro;}"
                "function pedir(ruta,cuerpo){return fetch(API+ruta,{method:'POST',credentials:'include',headers:{'Content-Type':'text/plain'},body:cuerpo})"
                ".then(function(r){if(!r.ok)throw new Error('rechazado');});}")
    if accion == "guardar":
        cuerpo = "if(!B){antigua();return;}pedir('/t/sesion',B).catch(antigua).then(function(){P.location.reload();});"
    elif accion == "migrar":
        cuerpo = ("if(!B||D.cookie.indexOf(N+'=')<0)return;"
                  "try{if(P.sessionStorage.getItem('pj_cookie_migrada'))return;P.sessionStorage.setItem('pj_cookie_migrada','1');}catch(e){return;}"
                  "pedir('/t/sesion',B).then(function(){P.location.reload();}).catch(function(){});")
    else:
        cuerpo = ("pedir('/t/sesion/cerrar','').catch(function(){});"
                  "D.cookie=N+'=; Max-Age=0; Path=/; SameSite=Lax'+seguro;")
    return "<script>(function(){" + cabecera + cuerpo + "})();</script>"


# TITULO APLICAR PENDIENTE

def aplicar_pendiente() -> None:
    """Escribe o borra la cookie en el navegador si hay una acción pendiente; luego la olvida. Sin acción pendiente, revisa una vez por pestaña si la cookie es la antigua.

    Emite un componente de altura 0. Con el servidor de datos (`SERVIDOR_SECRETO`), guardar detiene la ejecución (`st.stop()`) hasta que el navegador recargue la página con la cookie
    ya puesta: así los gráficos y los precios en vivo nunca piden datos antes de que la cookie exista. Atributos de la cookie: `Max-Age` de DIAS_DURACION días (sobrevive al cierre del
    navegador), `Path=/`, `HttpOnly`, `SameSite=Lax` y `Secure` cuando la plataforma va por HTTPS."""
    accion = st.session_state.pop(_PENDIENTE, None)
    con_servidor = boleto_sesion.configurado()
    if not accion:
        token = leer()
        if con_servidor and token and st.session_state.get("usuario_autenticado") and not st.session_state.get(_REVISADA):
            st.session_state[_REVISADA] = True
            components.html(_script("migrar", token), height=0)
        return
    tipo, token = accion
    if tipo == "guardar":
        components.html(_script("guardar", token), height=0)
        if con_servidor:
            st.stop()
    elif con_servidor:
        components.html(_script("borrar", ""), height=0)
    else:
        nombre = json.dumps(NOMBRE_COOKIE)
        components.html(
            "<script>(function(){var D;try{D=window.parent.document;}catch(e){return;}"
            "var seguro=(window.parent.location.protocol==='https:')?'; Secure':'';"
            f"D.cookie={nombre}+'=; Max-Age=0; Path=/; SameSite=Lax'+seguro;}})();</script>", height=0)


# -------------------------------------------------------------------------------------------------------
# -------------------------------------- FIN Piña y Jara cookie .PY -------------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
