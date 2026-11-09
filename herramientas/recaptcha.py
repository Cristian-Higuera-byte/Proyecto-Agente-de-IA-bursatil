# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ------------------------------------ INICIO Piña y Jara recaptcha .PY ---------------------------------
# -------------------------------------------------------------------------------------------------------

"""Verificación en el servidor de los tokens de reCAPTCHA de Google (v3 y v2).

Cada formulario protegido hace dos cosas: el navegador obtiene un token de v3 (invisible, puntúa a la persona de 0 a 1) y, solo si ese puntaje es bajo, muestra el casillero
«No soy un robot» de v2. Aquí se comprueban esos tokens contra `https://www.google.com/recaptcha/api/siteverify` con las claves secretas, que nunca salen del servidor.

Las claves salen de `configuracion.py` (variables RECAPTCHA_* del .env). Si faltan, la protección queda apagada y todo se acepta (desarrollo); con las cuatro claves puestas se exige.
No usa Streamlit, de modo que se puede probar sin la interfaz.
"""
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Optional

import configuracion

# Dirección de verificación de Google y segundos máximos que se espera su respuesta antes de rechazar el envío.
URL_VERIFICACION = "https://www.google.com/recaptcha/api/siteverify"
ESPERA_SEGUNDOS = 6.0

# Textos que ve la persona (sin detalles técnicos).
MENSAJE_CONFIRMAR = "Confirma que no eres un robot para continuar."
MENSAJE_REINTENTAR = "No pudimos verificar que eres una persona. Inténtalo de nuevo."
MENSAJE_SIN_SERVICIO = "No pudimos contactar al servicio de verificación. Inténtalo de nuevo en un minuto."


# TITULO VEREDICTO

@dataclass
class Veredicto:
    """Resultado de verificar un envío: `ok` si pasa, `pedir_v2` si hay que mostrar el casillero de v2, `mensaje` para la persona y `puntaje` de v3 (None si no hubo)."""
    ok: bool
    pedir_v2: bool = False
    mensaje: str = ""
    puntaje: Optional[float] = None


# TITULO ACTIVO

def activo() -> bool:
    """True si están puestas las cuatro claves de reCAPTCHA (sitio y secreta de v3 y de v2); sin ellas la protección está apagada."""
    return configuracion.RECAPTCHA_ACTIVO


# TITULO CONSULTAR

def _consultar(secreta: str, token: str, ip: Optional[str] = None) -> Optional[dict]:
    """Envía el token a Google y devuelve su respuesta como diccionario, o None si no se pudo contactar el servicio o la respuesta no es válida.

    La clave secreta viaja solo en esta petición; nunca se escribe en mensajes ni registros."""
    datos = {"secret": secreta, "response": token}
    if ip:
        datos["remoteip"] = ip
    peticion = urllib.request.Request(URL_VERIFICACION, data=urllib.parse.urlencode(datos).encode("utf-8"), method="POST")
    try:
        with urllib.request.urlopen(peticion, timeout=ESPERA_SEGUNDOS) as respuesta:
            cuerpo = json.loads(respuesta.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None
    return cuerpo if isinstance(cuerpo, dict) else None


# TITULO VERIFICAR

def verificar(accion: str, token_v3: str = "", token_v2: str = "", ip: Optional[str] = None) -> Veredicto:
    """Decide si un envío del formulario `accion` (por ejemplo «login») pasa la protección.

    Con la protección apagada acepta todo. Con un token de v2 lo comprueba contra la clave de v2. Sin él, comprueba el de v3: debe ser válido, de la misma acción y con
    puntaje de `configuracion.RECAPTCHA_UMBRAL` o más; si falta, es inválido o el puntaje es bajo, pide el casillero de v2. Si Google no responde, rechaza (falla cerrado)
    sin pedir v2, porque el casillero tampoco se podría comprobar."""
    if not activo():
        return Veredicto(True)
    if token_v2:
        respuesta = _consultar(configuracion.RECAPTCHA_V2_SECRETA, token_v2, ip)
        if respuesta is None:
            return Veredicto(False, mensaje=MENSAJE_SIN_SERVICIO)
        if respuesta.get("success") is True:
            return Veredicto(True)
        return Veredicto(False, pedir_v2=True, mensaje=MENSAJE_REINTENTAR)
    if not token_v3:
        return Veredicto(False, pedir_v2=True, mensaje=MENSAJE_CONFIRMAR)
    respuesta = _consultar(configuracion.RECAPTCHA_V3_SECRETA, token_v3, ip)
    if respuesta is None:
        return Veredicto(False, mensaje=MENSAJE_SIN_SERVICIO)
    try:
        puntaje = float(respuesta.get("score")) if respuesta.get("score") is not None else None
    except (TypeError, ValueError):
        puntaje = None
    if respuesta.get("success") is True and respuesta.get("action") == accion and puntaje is not None and puntaje >= configuracion.RECAPTCHA_UMBRAL:
        return Veredicto(True, puntaje=puntaje)
    return Veredicto(False, pedir_v2=True, mensaje=MENSAJE_CONFIRMAR, puntaje=puntaje)


# -------------------------------------------------------------------------------------------------------
# ------------------------------------- FIN Piña y Jara recaptcha .PY -----------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
