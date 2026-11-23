# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ------------------------------- INICIO Piña y Jara aceptaciones_legales .PY ---------------------------
# -------------------------------------------------------------------------------------------------------

"""
aceptaciones_legales.py
-----------------------
Constancia de qué documentos y funciones aceptó cada usuario, con su versión, la fecha y, cuando corresponde, el alcance (demo o real) y el detalle (por ejemplo, qué vigilancia).

Se guarda en la tabla `aceptaciones_legales` (herramientas/sql/aceptaciones_legales.sql). Qué se acepta:
  - Documentos generales: «terminos», «privacidad» y «riesgo» (versión `VERSION` de componentes_plataforma/legal/contenido.py). Se aceptan juntos al crear la cuenta o, después, en la puerta de aceptación.
  - Funciones: «one_click», «vigilancia» y «copytrading», cada una con su versión de `VERSIONES_FUNCION`, el alcance (demo o real) y el detalle de lo aceptado (el id de la vigilancia, la estrategia copiada).

V22 de la auditoría: (1) el registro es ATÓMICO: todas las filas van en una sola sentencia, así que se guardan todas o ninguna (no queda una aceptación a medias). (2) Falla cerrado: si no se puede
guardar o consultar, se informa False y la función queda pendiente; ya no se da por aceptado lo que no consta. (3) `vigentes` y `exigir` comprueban en el servidor que la ÚLTIMA aceptación de cada
documento es de la versión vigente; un cambio de versión obliga a aceptar de nuevo, y llamar directamente a la función sin haber aceptado la rechaza.
"""
from typing import Any, Iterable, Optional

from herramientas import gestor_autenticacion

# Documentos generales y funciones que se pueden aceptar, y la versión vigente de cada función (se sube cuando cambia su texto material).
DOCUMENTOS_GENERALES = ("terminos", "privacidad", "riesgo")
VERSIONES_FUNCION = {"one_click": "1.0", "vigilancia": "1.0", "copytrading": "1.0"}
_PERMITIDOS = frozenset(DOCUMENTOS_GENERALES) | frozenset(VERSIONES_FUNCION)
_ALCANCES = ("demo", "real")
_TABLA = "aceptaciones_legales"


class AceptacionPendiente(Exception):
    """Falta la constancia vigente de la aceptación de un documento o de una función."""


# TITULO CLIENTE

def _cliente(cliente: Any = None) -> Any:
    """El cliente de base de datos dado o el de la autenticación (None si no hay conexión)."""
    return cliente if cliente is not None else gestor_autenticacion._supabase


# TITULO REGISTRAR

def registrar(usuario_id, documentos: Iterable[str], version: str, alcance: Optional[str] = None, detalle: Optional[str] = None, cliente: Any = None) -> bool:
    """Guarda la aceptación de `documentos` (lista de claves) en la `version` dada, con el `alcance` (demo o real) y el `detalle` si corresponden.

    Todas las filas van en UNA sola sentencia: se guardan todas o ninguna. Devuelve True solo si la base confirma tantas filas como documentos; False si no hay conexión, falta la tabla, hay un
    documento desconocido, el alcance no es válido o falla el guardado (en ese caso no queda nada guardado)."""
    cliente, documentos = _cliente(cliente), list(documentos)
    if cliente is None or usuario_id is None or not documentos or any(d not in _PERMITIDOS for d in documentos) or (alcance is not None and alcance not in _ALCANCES):
        return False
    filas = [{"usuario_id": usuario_id, "documento": d, "version": str(version), "alcance": alcance, "detalle": None if detalle is None else str(detalle)[:500]} for d in documentos]
    try:
        guardadas = cliente.table(_TABLA).insert(filas).execute().data or []
    except Exception:
        return False
    return len(guardadas) == len(filas)


# TITULO ULTIMA VERSION ACEPTADA

def ultima_version(usuario_id, documento: str, cliente: Any = None) -> Optional[str]:
    """Devuelve la última versión del documento que aceptó el usuario, o None si no la aceptó o no se puede consultar."""
    cliente = _cliente(cliente)
    if cliente is None or usuario_id is None:
        return None
    try:
        filas = cliente.table(_TABLA).select("version").eq("usuario_id", usuario_id).eq("documento", documento).order("aceptada_en", desc=True).limit(1).execute()
        return filas.data[0]["version"] if filas.data else None
    except Exception:
        return None


# TITULO VIGENTES

def vigentes(usuario_id, documentos: Iterable[str], version: str, detalle: Optional[str] = None, cliente: Any = None) -> bool:
    """True si la ÚLTIMA aceptación de cada uno de `documentos` es de la `version` dada (y, si se indica, del mismo `detalle`).

    Falla cerrado: sin conexión, con la tabla ausente o ante cualquier error devuelve False (no consta la aceptación)."""
    cliente, documentos = _cliente(cliente), list(documentos)
    if cliente is None or usuario_id is None or not documentos:
        return False
    try:
        for documento in documentos:
            consulta = cliente.table(_TABLA).select("version").eq("usuario_id", usuario_id).eq("documento", documento)
            if detalle is not None:
                consulta = consulta.eq("detalle", str(detalle)[:500])
            filas = consulta.order("aceptada_en", desc=True).limit(1).execute().data or []
            if not filas or str(filas[0]["version"]) != str(version):
                return False
    except Exception:
        return False
    return True


# TITULO EXIGIR

def exigir(usuario_id, funcion: str, detalle: Optional[str] = None, cliente: Any = None) -> None:
    """Lanza AceptacionPendiente si el usuario no tiene la aceptación vigente de `funcion` (y del mismo `detalle`, si se indica). Es la comprobación del servidor antes de habilitar la función."""
    if funcion not in VERSIONES_FUNCION:
        raise AceptacionPendiente(f"Función desconocida: {funcion}.")
    if not vigentes(usuario_id, [funcion], VERSIONES_FUNCION[funcion], detalle=detalle, cliente=cliente):
        raise AceptacionPendiente("Falta tu aceptación vigente de las condiciones de esta función: acéptalas para continuar.")


# -------------------------------------------------------------------------------------------------------
# -------------------------------- FIN Piña y Jara aceptaciones_legales .PY -----------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
