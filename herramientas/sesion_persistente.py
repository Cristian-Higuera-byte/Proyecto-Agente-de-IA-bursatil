# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ------------------------------ INICIO Piña y Jara sesion_persistente .PY ------------------------------
# -------------------------------------------------------------------------------------------------------

"""
sesion_persistente.py
---------------------
Sesiones que sobreviven al cierre del navegador y al reinicio del servidor («mantener sesión iniciada»).

Cómo funciona:
  - Al iniciar sesión se crea un token aleatorio. El navegador lo guarda en una cookie (la escribe acceso/cookie.py) y aquí se guarda en
    Supabase solo su hash SHA-256, con el usuario y la fecha de vencimiento (tabla `sesiones_persistentes`, herramientas/sql/).
  - Al abrir la web sin sesión, la cookie llega al servidor; `validar` busca su hash en la tabla y, si no venció, devuelve el usuario.
  - Cerrar sesión borra la fila (`revocar`), de modo que la cookie queda inservible aunque alguien la conserve.
Desde el 12-11-2026 esta cookie es lo ÚNICO que mantiene la sesión (la dirección ya no lleva `?s=`): cada recarga de la página (F5, un enlace del menú) la valida
aquí. Por eso `validar` recuerda 30 segundos las sesiones ya comprobadas, para que las recargas seguidas no repitan las consultas a la base.
"""
import hashlib
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from herramientas import gestor_autenticacion

# Nombre de la cookie del navegador y días que dura una sesión persistente desde que se crea.
from herramientas.boleto_sesion import NOMBRE_COOKIE  # noqa: F401 - se reexporta: la usan acceso/cookie.py y las pruebas
DIAS_DURACION = 30
# Máximo de dispositivos con sesión abierta por usuario; al iniciar sesión en uno más se cierra la sesión que hace más tiempo no se usa.
MAX_DISPOSITIVOS = 5
# Segundos que `validar` recuerda una sesión ya comprobada, y las sesiones recordadas {hash del token: (usuario, instante)}. Cerrar sesión (`revocar`, `revocar_todas`) las olvida al instante.
MEMORIA_S = 30
_validadas: dict = {}
# Horas sin usarse tras las cuales una sesión vence aunque no haya cumplido sus DIAS_DURACION (variable SESION_INACTIVIDAD_HORAS del .env; por defecto 24)
INACTIVIDAD_HORAS = float(os.environ.get("SESION_INACTIVIDAD_HORAS", "24") or 24)
# Cada cuántos segundos como máximo se anota el último uso de una sesión (para no escribir en la base en cada consulta)
ACTUALIZAR_USO_S = 60
# Duración de una sesión SIN «mantener la sesión iniciada»: la cookie muere al cerrar el navegador y, aunque no se cierre, la sesión vence a las 12 horas
HORAS_SESION_CORTA = 12
# La sesión persistente se ROTA: al volver a entrar con una cookie de más de estos días se emite una nueva y la vieja se anula (así una cookie robada deja de servir tarde o temprano)
DIAS_ROTACION = 7
# Segundos que la cookie vieja sigue valiendo tras rotarla: otra pestaña del mismo navegador pudo haber empezado a cargar con ella
GRACIA_ROTACION_S = 120


# TITULO HASH

def _hash(token: str) -> str:
    """Devuelve el hash SHA-256 (hexadecimal) de un token; es lo único que se guarda en la base de datos."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# TITULO CREAR

def crear(usuario_id, dispositivo: str = "", reemplaza_token: str = "", persistente: bool = True, rotando: bool = False) -> Optional[str]:
    """Crea una sesión para el usuario y devuelve el token que debe guardar la cookie.

    Recibe el `usuario_id`, un resumen del navegador (`dispositivo`) y, si el navegador ya traía una cookie, ese token en `reemplaza_token`: su fila se borra
    para que iniciar sesión varias veces en el mismo navegador no acumule filas. Con `persistente` (la persona pidió «mantener la sesión iniciada») la sesión dura DIAS_DURACION
    días; sin él, HORAS_SESION_CORTA horas y la cookie muere al cerrar el navegador. Guarda en la base el hash del token y su vencimiento, borra las sesiones ya vencidas y deja como
    máximo MAX_DISPOSITIVOS por usuario, cerrando las que hace más tiempo no se usan (salvo al rotar: `rotando` no cambia la cantidad de dispositivos). Devuelve None si no hay
    conexión con la base o si falla el guardado: el inicio de sesión sigue funcionando, solo que sin «mantener sesión».
    """
    cliente = gestor_autenticacion._supabase
    if cliente is None or usuario_id is None:
        return None
    token = secrets.token_urlsafe(32)
    ahora = datetime.now(timezone.utc)
    vence = ahora + (timedelta(days=DIAS_DURACION) if persistente else timedelta(hours=HORAS_SESION_CORTA))
    try:
        cliente.table("sesiones_persistentes").delete().lt("expira_en", ahora.isoformat()).execute()
        if reemplaza_token:
            _validadas.pop(_hash(reemplaza_token), None)
            cliente.table("sesiones_persistentes").delete().eq("token_hash", _hash(reemplaza_token)).execute()
        cliente.table("sesiones_persistentes").insert({
            "usuario_id": usuario_id,
            "token_hash": _hash(token),
            "expira_en": vence.isoformat(),
            "dispositivo": (dispositivo or "")[:160],
        }).execute()
        if not rotando:
            # Tope de dispositivos: se conservan los más recientes (por último uso) y se borran los demás.
            filas = cliente.table("sesiones_persistentes").select("id").eq("usuario_id", usuario_id).order("ultimo_uso", desc=True).execute()
            for fila in (filas.data or [])[MAX_DISPOSITIVOS:]:
                cliente.table("sesiones_persistentes").delete().eq("id", fila["id"]).execute()
    except Exception:
        return None
    return token


# TITULO ROTAR SI TOCA

def rotar_si_toca(token: str, dispositivo: str = "") -> Optional[str]:
    """Si la sesión de ese token tiene más de DIAS_ROTACION días, crea otra para el mismo usuario y devuelve el token nuevo (que debe guardar la cookie); si no toca, o falla, devuelve None.

    La sesión vieja no se borra enseguida: se deja vigente GRACIA_ROTACION_S segundos más, porque otra pestaña del mismo navegador pudo haber empezado a cargar con la cookie anterior, y
    luego vence sola. La nueva conserva el tipo de la vieja (persistente o corta). Así una cookie robada deja de servir a más tardar a los DIAS_ROTACION días de uso."""
    cliente = gestor_autenticacion._supabase
    if cliente is None or not token:
        return None
    try:
        fila = cliente.table("sesiones_persistentes").select("id, usuario_id, creada_en, expira_en").eq("token_hash", _hash(token)).limit(1).execute().data
        if not fila:
            return None
        creada, vence, ahora = _fecha(fila[0].get("creada_en")), _fecha(fila[0].get("expira_en")), datetime.now(timezone.utc)
        if creada is None or vence is None or (ahora - creada).total_seconds() < DIAS_ROTACION * 86400:
            return None
        nuevo = crear(fila[0]["usuario_id"], dispositivo, persistente=(vence - creada) > timedelta(days=1), rotando=True)
        if not nuevo:
            return None
        cliente.table("sesiones_persistentes").update({"expira_en": (ahora + timedelta(seconds=GRACIA_ROTACION_S)).isoformat()}).eq("id", fila[0]["id"]).execute()
        _validadas.pop(_hash(token), None)
        return nuevo
    except Exception:  # noqa: BLE001 - si no se puede rotar, la sesión sigue como estaba
        return None


# TITULO FECHA

def _fecha(texto):
    """Convierte un texto de fecha ISO de la base de datos a datetime con zona horaria, o None si falta o no se entiende."""
    if not texto:
        return None
    try:
        fecha = datetime.fromisoformat(str(texto).replace("Z", "+00:00"))
    except ValueError:
        return None
    return fecha if fecha.tzinfo else fecha.replace(tzinfo=timezone.utc)


# TITULO CONSULTAR

def consultar(token: str, memoria_s: float = MEMORIA_S) -> dict:
    """Comprueba la sesión de ese token y devuelve {"usuario": {id, nombre, email} | None, "incierto": bool}.

    `usuario` es None si el token no existe, venció, lleva más de INACTIVIDAD_HORAS sin usarse (la fila se borra) o se revocó. `incierto` es True cuando NO se pudo comprobar
    (la base no responde): en ese caso `usuario` trae el último resultado conocido de ese token, si lo hay. Un resultado ya comprobado se recuerda `memoria_s` segundos (el servidor
    de datos usa 5 para que cerrar sesión corte los canales en vivo en segundos). El último uso se anota como mucho cada ACTUALIZAR_USO_S segundos."""
    cliente = gestor_autenticacion._supabase
    if not token:
        return {"usuario": None, "incierto": False}
    if cliente is None:
        return {"usuario": None, "incierto": True}
    huella = _hash(token)
    recordada = _validadas.get(huella)
    ahora = time.time()
    if recordada is not None and ahora - recordada[1] < memoria_s:
        return {"usuario": dict(recordada[0]), "incierto": False}
    try:
        fila = cliente.table("sesiones_persistentes").select("id, usuario_id, expira_en, ultimo_uso").eq("token_hash", huella).limit(1).execute()
        if not fila.data:
            _validadas.pop(huella, None)
            return {"usuario": None, "incierto": False}
        sesion = fila.data[0]
        instante = datetime.now(timezone.utc)
        ultimo = _fecha(sesion.get("ultimo_uso"))
        if _fecha(sesion.get("expira_en")) is None or _fecha(sesion["expira_en"]) <= instante or (ultimo is not None and (instante - ultimo).total_seconds() > INACTIVIDAD_HORAS * 3600):
            _validadas.pop(huella, None)
            cliente.table("sesiones_persistentes").delete().eq("id", sesion["id"]).execute()      # vencida o inactiva: se borra, ya no sirve
            return {"usuario": None, "incierto": False}
        if ultimo is None or (instante - ultimo).total_seconds() > ACTUALIZAR_USO_S:
            cliente.table("sesiones_persistentes").update({"ultimo_uso": instante.isoformat()}).eq("id", sesion["id"]).execute()
        usuario = cliente.table("usuarios").select("id, nombre, email").eq("id", sesion["usuario_id"]).limit(1).execute()
        if not usuario.data:
            _validadas.pop(huella, None)
            return {"usuario": None, "incierto": False}
        datos = usuario.data[0]
        validado = {"id": datos.get("id"), "nombre": datos.get("nombre"), "email": datos.get("email")}
        if len(_validadas) > 2000:
            _validadas.clear()
        _validadas[huella] = (validado, ahora)
        return {"usuario": dict(validado), "incierto": False}
    except Exception:  # noqa: BLE001 - la base no responde: se devuelve lo último que se sabía
        return {"usuario": dict(recordada[0]) if recordada is not None else None, "incierto": True}


# TITULO VALIDAR

def validar(token: str) -> Optional[dict]:
    """Devuelve el usuario ({id, nombre, email}) dueño del token, o None si no existe, venció, está inactiva o falla la consulta (ver `consultar`)."""
    return consultar(token)["usuario"]


# TITULO REVOCAR

def revocar(token: str) -> None:
    """Borra la sesión persistente de ese token (cerrar sesión); no hace nada si no existe o falla la conexión."""
    if token:
        _validadas.pop(_hash(token), None)
    cliente = gestor_autenticacion._supabase
    if cliente is None or not token:
        return
    try:
        cliente.table("sesiones_persistentes").delete().eq("token_hash", _hash(token)).execute()
    except Exception:
        pass


# TITULO REVOCAR TODAS

def revocar_todas(usuario_id) -> None:
    """Borra todas las sesiones persistentes de un usuario (por ejemplo, tras cambiar su contraseña)."""
    for hash_token in [h for h, (u, _) in _validadas.items() if str(u.get("id")) == str(usuario_id)]:
        _validadas.pop(hash_token, None)
    cliente = gestor_autenticacion._supabase
    if cliente is None or usuario_id is None:
        return
    try:
        cliente.table("sesiones_persistentes").delete().eq("usuario_id", usuario_id).execute()
    except Exception:
        pass


# -------------------------------------------------------------------------------------------------------
# ------------------------------- FIN Piña y Jara sesion_persistente .PY --------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
