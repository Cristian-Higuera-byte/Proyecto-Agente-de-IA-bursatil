# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# --------------------------------------- INICIO Piña y Jara roles .PY ----------------------------------
# -------------------------------------------------------------------------------------------------------

"""Roles de los usuarios de la plataforma: «usuario» (el de todos) y «root» (administrador).

NOMBRE DEL ARCHIVO: herramientas/roles.py

Un usuario es root SOLO si su fila de la tabla `usuarios` tiene la columna `rol` en «root» (herramientas/sql/roles.sql) Y su correo está verificado (cuando la verificación de correo
está activa). El rol se asigna desde la base de datos (nunca desde la plataforma) a un usuario que ya existe y ya confirmó su correo, o con `crear_usuario_root.py`, que solo CREA
cuentas nuevas. Antes (V10 de la auditoría) también bastaba con que el correo estuviera en la variable `ROOT_CORREOS` y, en el modo de un solo usuario, todos eran root: un correo no es
una prueba de identidad (quien se registre primero con él obtenía el rol) y el modo de desarrollo no puede conceder privilegios; ambas vías se eliminaron.

Solo los root ven las secciones internas (hoy, el Laboratorio) y pueden usar las acciones de administrador (la parada global del operador), porque muestran o cambian datos de toda la
plataforma: costos, demanda de planes, correos de la lista de espera y consumo de IA de todos los usuarios.

Cómo se comprueba:
  * `es_root(usuario)` es para dibujar la interfaz: recuerda el rol leído de la base VIGENCIA_ROL segundos (pocos, para que bajar el rol rija casi de inmediato).
  * `exigir_root()` es para cada acción o dato interno de administrador: lee el rol SIN memoria y lanza PermissionError si quien actúa (el usuario de la sesión, nunca un valor que mande el
    navegador) no es root. Así una acción no depende de que la pantalla haya ocultado el botón: invocarla directamente también se rechaza, y un rol revocado durante una sesión activa deja de
    servir en la siguiente llamada.
  * Se falla cerrado: si la columna `rol` no existe todavía o la base falla, nadie es root.
  * En el modo de un solo usuario (desarrollo, sin `CAPITAL_MULTIUSUARIO`) NADIE es root, salvo que se pida expresamente con `ROOT_MODO_LEGADO=true` en el .env de ese equipo.
"""
import os
import threading
import time
from typing import Any

from herramientas import gestor_autenticacion
from herramientas.backends import sesiones_capital

# Valores del rol
ROL_USUARIO = "usuario"
ROL_ROOT = "root"
# Segundos que se recuerda el rol leído de la base de datos al dibujar la interfaz (`exigir_root` no usa memoria)
VIGENCIA_ROL = 5.0
# Solo para un equipo de desarrollo en modo de un solo usuario: ROOT_MODO_LEGADO=true en su .env lo convierte en administrador. Nunca debe estar en el servidor.
ROOT_MODO_LEGADO: bool = os.getenv("ROOT_MODO_LEGADO", "").strip().lower() in ("1", "true", "si", "sí", "yes")
# Roles recordados: id del usuario -> (instante de lectura, rol, correo verificado). El rol es None si no se pudo leer.
_RECORDADOS: dict[str, tuple[float, str | None, bool | None]] = {}
_CANDADO = threading.Lock()


# TITULO LEER ROL

def _leer_rol(usuario_id: Any, memoria_s: float) -> tuple[str | None, bool | None]:
    """(rol, correo verificado) del usuario según la tabla `usuarios`; (None, None) si no hay conexión, no existe la columna o falla la consulta.

    `memoria_s` son los segundos que se acepta un valor ya leído (0 = consultar siempre). Si la columna de verificación del correo no existe, el segundo valor es None."""
    cliente = gestor_autenticacion._supabase
    if cliente is None or usuario_id in (None, ""):
        return None, None
    clave, ahora = str(usuario_id), time.time()
    with _CANDADO:
        guardado = _RECORDADOS.get(clave)
    if guardado is not None and ahora - guardado[0] < memoria_s:
        return guardado[1], guardado[2]
    try:
        try:
            filas = cliente.table("usuarios").select("rol, correo_verificado").eq("id", int(usuario_id)).limit(1).execute().data
        except Exception:  # noqa: BLE001 - la verificación del correo puede no estar instalada: se lee solo el rol
            filas = cliente.table("usuarios").select("rol").eq("id", int(usuario_id)).limit(1).execute().data
        rol = filas[0].get("rol") if filas else None
        verificado = filas[0].get("correo_verificado") if filas else None
    except Exception:  # noqa: BLE001 - sin la columna o sin base no se concede nada
        rol, verificado = None, None
    with _CANDADO:
        _RECORDADOS[clave] = (ahora, rol, verificado)
    return rol, verificado


# TITULO OLVIDAR

def olvidar(usuario_id: Any) -> None:
    """Descarta el rol recordado del usuario (úsalo tras cambiar su rol en la base de datos para que rija de inmediato)."""
    with _CANDADO:
        _RECORDADOS.pop(str(usuario_id), None)


# TITULO ES ROOT DE

def _es_root_de(usuario_id: Any, memoria_s: float) -> bool:
    """True si ese usuario tiene el rol root guardado y, con la verificación de correo activa, su correo está verificado."""
    rol, verificado = _leer_rol(usuario_id, memoria_s)
    if rol != ROL_ROOT:
        return False
    return not (gestor_autenticacion.verificacion_activa() and verificado is not True)


# TITULO ES ROOT

def es_root(usuario: Any) -> bool:
    """True si `usuario` (el diccionario de la sesión, con `id`) es administrador; para dibujar la interfaz (usa una memoria corta, ver VIGENCIA_ROL).

    Sin usuario o con un valor que no es un diccionario devuelve False. El correo del usuario NO cuenta: solo el rol guardado en la base de datos. Las acciones de administrador no
    deben apoyarse en esta función sino en `exigir_root`."""
    if not sesiones_capital.MULTIUSUARIO:
        return ROOT_MODO_LEGADO
    if not isinstance(usuario, dict):
        return False
    return _es_root_de(usuario.get("id"), VIGENCIA_ROL)


# TITULO ES ROOT ACTUAL

def es_root_actual() -> bool:
    """True si quien actúa ahora (el usuario de la sesión, según el servidor) es administrador; consulta la base de datos sin memoria."""
    if not sesiones_capital.MULTIUSUARIO:
        return ROOT_MODO_LEGADO
    clave = sesiones_capital.clave_actual()
    return len(clave) == 2 and _es_root_de(clave[0], 0.0)


# TITULO EXIGIR ROOT

def exigir_root() -> None:
    """Lanza PermissionError si quien actúa ahora no es administrador. Va al comienzo de cada acción o lectura de datos que solo debe hacer un administrador."""
    if not es_root_actual():
        raise PermissionError("Esta acción es solo para administradores de la plataforma.")


# -------------------------------------------------------------------------------------------------------
# ---------------------------------------- FIN Piña y Jara roles .PY ------------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
