# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ---------------------------- INICIO Piña y Jara idempotencia_ordenes .PY ------------------------------
# -------------------------------------------------------------------------------------------------------

"""
idempotencia_ordenes.py
-----------------------
Registro de intentos de orden para que una misma orden NO se abra dos veces (V05 de la auditoría).

El problema: si la respuesta del bróker se pierde (tiempo agotado, corte de red, error 5xx), la orden pudo abrirse igual, pero el programa lo ve como un fallo y la persona (o un
reintento automático) la envía otra vez. La solución tiene dos partes:
  1. CLAVE DE IDEMPOTENCIA: cada orden lleva una clave que pone quien la origina (un clic del panel, una propuesta confirmada, una copia de copy trading, una petición del servidor).
     Antes de salir hacia el bróker la clave se reserva de forma atómica (INSERT con clave primaria). Si la misma clave llega otra vez, NO se reenvía: se devuelve el resultado
     guardado o, si el resultado aún se desconoce, se verifica con el bróker.
  2. RECONCILIACIÓN: cuando el resultado es incierto, el intento queda en estado «incierta» y se resuelve preguntándole al bróker (la confirmación por su referencia o, si no hay,
     buscando la posición u orden pendiente que coincide). La consulta al bróker la hace `capital_nucleo`; este módulo solo guarda el estado.

Estados de un intento: `enviando` (reservada, aún sin respuesta), `incierta` (no se sabe si el bróker la aceptó), `confirmada` y `rechazada` (finales).

Las claves se separan por usuario y cuenta (demo o real): la misma clave de dos personas no se mezcla. El estado vive en un archivo SQLite propio (data/intentos_orden.db) para
que lo vean todos los procesos (Streamlit, servidor de datos, motor de vigilancias) sin depender de que la base de datos principal esté disponible justo al enviar una orden.
"""
import json
import sqlite3
import threading
import time
import uuid
from contextlib import closing, contextmanager
from contextvars import ContextVar
from pathlib import Path

DIR_DATOS = Path(__file__).resolve().parent.parent / "data"
RUTA_DB = DIR_DATOS / "intentos_orden.db"

# Segundos que un intento puede quedar en «enviando» antes de tratarlo como incierto (el proceso pudo morir entre la reserva y la respuesta)
ESPERA_ENVIANDO = 60
# Segundos desde el envío tras los cuales, si el bróker no muestra ninguna orden que coincida, se da por no recibida
GRACIA_NO_RECIBIDA = 20
# Los intentos finales se borran pasado este tiempo (segundos)
CONSERVAR = 7 * 24 * 3600

ENVIANDO, INCIERTA, CONFIRMADA, RECHAZADA = "enviando", "incierta", "confirmada", "rechazada"

_CLAVE: ContextVar = ContextVar("clave_idempotencia_orden", default=None)
_PREPARADA: Path | None = None
_CANDADO = threading.Lock()


# TITULO CON CLAVE

@contextmanager
def con_clave(clave: str | None):
    """Dentro del bloque, toda orden que se abra usa `clave` como clave de idempotencia (así viaja por las capas intermedias sin cambiar sus firmas)."""
    señal = _CLAVE.set(str(clave) if clave else None)
    try:
        yield
    finally:
        _CLAVE.reset(señal)


# TITULO CLAVE ACTUAL

def clave_actual() -> str | None:
    """Clave fijada con `con_clave` en este hilo, o None si quien llama no puso ninguna."""
    return _CLAVE.get()


# TITULO CONECTAR

def _conectar() -> sqlite3.Connection:
    """Abre una conexión nueva al archivo de intentos (lo crea con su tabla la primera vez en este proceso). Quien la llama debe cerrarla."""
    global _PREPARADA
    DIR_DATOS.mkdir(exist_ok=True)
    con = sqlite3.connect(RUTA_DB, timeout=10)
    con.row_factory = sqlite3.Row
    if _PREPARADA != RUTA_DB:
        with _CANDADO:
            con.execute("CREATE TABLE IF NOT EXISTS intentos (k TEXT PRIMARY KEY, usuario TEXT NOT NULL, cuenta TEXT NOT NULL, tipo TEXT NOT NULL, epic TEXT NOT NULL, "
                        "direccion TEXT NOT NULL, tamano REAL NOT NULL, estado TEXT NOT NULL, referencia TEXT, resultado TEXT, extra TEXT, creado REAL NOT NULL, "
                        "enviado REAL, actualizado REAL NOT NULL)")
            con.execute("CREATE INDEX IF NOT EXISTS intentos_dueno ON intentos (usuario, cuenta, estado)")
            con.commit()
            _PREPARADA = RUTA_DB
    return con


# TITULO CLAVE COMPLETA

def _clave_completa(dueno: tuple[str, str], clave: str) -> str:
    """Clave guardada: usuario, cuenta y la clave de quien origina la orden (separadas para que dos personas no se pisen)."""
    return f"{dueno[0]}:{dueno[1]}:{clave}"


# TITULO NUEVA CLAVE

def nueva_clave() -> str:
    """Clave aleatoria para quien no trae una (cada llamada cuenta como una orden distinta, pero igual queda registrada para reconciliarla)."""
    return "auto-" + uuid.uuid4().hex


# TITULO COMENZAR

def comenzar(dueno: tuple[str, str], clave: str, tipo: str, epic: str, direccion: str, tamano: float, extra: dict | None = None) -> dict:
    """Reserva la clave de forma atómica antes de enviar la orden.

    Devuelve {"nuevo": True, "k": clave_guardada} si esta llamada debe enviar la orden, o {"nuevo": False, "fila": fila_existente} si la clave ya estaba usada."""
    k, ahora = _clave_completa(dueno, clave), time.time()
    with closing(_conectar()) as con:
        try:
            with con:
                con.execute("DELETE FROM intentos WHERE estado IN (?, ?) AND actualizado < ?", (CONFIRMADA, RECHAZADA, ahora - CONSERVAR))
                con.execute("INSERT INTO intentos (k, usuario, cuenta, tipo, epic, direccion, tamano, estado, extra, creado, actualizado) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                            (k, dueno[0], dueno[1], tipo, epic, direccion.upper(), float(tamano), ENVIANDO, json.dumps(extra or {}), ahora, ahora))
            return {"nuevo": True, "k": k}
        except sqlite3.IntegrityError:
            return {"nuevo": False, "fila": dict(con.execute("SELECT * FROM intentos WHERE k = ?", (k,)).fetchone())}


# TITULO LEER

def leer(k: str) -> dict | None:
    """Fila completa de un intento por su clave guardada, o None si no existe."""
    with closing(_conectar()) as con:
        fila = con.execute("SELECT * FROM intentos WHERE k = ?", (k,)).fetchone()
    return dict(fila) if fila else None


# TITULO MARCAR ENVIO

def marcar_envio(k: str) -> None:
    """Anota el instante en que se mandó la petición al bróker (desde ahí corre el plazo para dar la orden por no recibida)."""
    with closing(_conectar()) as con, con:
        con.execute("UPDATE intentos SET enviado = ?, actualizado = ? WHERE k = ?", (time.time(), time.time(), k))


# TITULO GUARDAR REFERENCIA

def guardar_referencia(k: str, referencia: str) -> None:
    """Guarda la referencia (`dealReference`) que el bróker devolvió: con ella se puede confirmar el resultado aunque se pierda lo demás."""
    with closing(_conectar()) as con, con:
        con.execute("UPDATE intentos SET referencia = ?, actualizado = ? WHERE k = ?", (referencia, time.time(), k))


# TITULO RESOLVER

def resolver(k: str, estado: str, resultado: dict) -> None:
    """Fija el estado del intento y el resultado que se devolverá si la misma clave vuelve a llegar."""
    with closing(_conectar()) as con, con:
        con.execute("UPDATE intentos SET estado = ?, resultado = ?, actualizado = ? WHERE k = ?", (estado, json.dumps(resultado), time.time(), k))


# TITULO ES INCIERTA

def es_incierta(fila: dict) -> bool:
    """True si el intento aún no tiene resultado final: está «incierta», o lleva demasiado en «enviando»."""
    if fila["estado"] == INCIERTA:
        return True
    return fila["estado"] == ENVIANDO and time.time() - (fila.get("enviado") or fila["creado"]) > ESPERA_ENVIANDO


# TITULO RESULTADO GUARDADO

def resultado_guardado(fila: dict) -> dict | None:
    """Resultado de un intento ya resuelto (para devolverlo sin reenviar), o None si aún no hay uno final."""
    if fila["estado"] in (CONFIRMADA, RECHAZADA) and fila.get("resultado"):
        return json.loads(fila["resultado"])
    return None


# TITULO INCIERTOS DEL DUENO

def inciertos_del_dueno(dueno: tuple[str, str], tipo: str | None = None, epic: str | None = None, direccion: str | None = None) -> list[dict]:
    """Intentos de ese usuario y cuenta que aún no se resolvieron (filtrables por tipo, instrumento y lado)."""
    consulta, valores = "SELECT * FROM intentos WHERE usuario = ? AND cuenta = ? AND estado IN (?, ?)", [dueno[0], dueno[1], ENVIANDO, INCIERTA]
    for columna, valor in (("tipo", tipo), ("epic", epic), ("direccion", direccion.upper() if direccion else None)):
        if valor:
            consulta += f" AND {columna} = ?"
            valores.append(valor)
    with closing(_conectar()) as con:
        filas = [dict(f) for f in con.execute(consulta, valores).fetchall()]
    return [f for f in filas if f["estado"] == INCIERTA or es_incierta(f)]


# TITULO DUENOS CON INCIERTOS

def duenos_con_inciertos() -> list[tuple[str, str]]:
    """(usuario, cuenta) con intentos sin resolver, para que el reconciliador de fondo sepa a quién revisar."""
    with closing(_conectar()) as con:
        filas = con.execute("SELECT DISTINCT usuario, cuenta FROM intentos WHERE estado IN (?, ?)", (ENVIANDO, INCIERTA)).fetchall()
    return [(f["usuario"], f["cuenta"]) for f in filas]


# TITULO IDS YA USADOS

def ids_usados(dueno: tuple[str, str]) -> set[str]:
    """dealId de las órdenes que ya quedaron confirmadas para ese usuario y cuenta: una posición con uno de estos ids no puede ser la de un intento incierto."""
    with closing(_conectar()) as con:
        filas = con.execute("SELECT resultado FROM intentos WHERE usuario = ? AND cuenta = ? AND estado = ?", (dueno[0], dueno[1], CONFIRMADA)).fetchall()
    usados = set()
    for f in filas:
        try:
            usados.add(str(json.loads(f["resultado"] or "{}").get("order", "")))
        except ValueError:
            continue
    return usados


# -------------------------------------------------------------------------------------------------------
# ----------------------------- FIN Piña y Jara idempotencia_ordenes .PY --------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
