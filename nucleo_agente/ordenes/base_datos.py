"""Base de datos (SQLite) de las órdenes: propuestas, auditoría, vigilancias e interruptor de emergencia.
El esquema vive en sql/ (ordenes.sql, vigilancias.sql) y las columnas añadidas después en columnas_nuevas.json."""
import json
import sqlite3
import threading
import uuid
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from nucleo_agente.ordenes.limites import LIMITES

_AQUI = Path(__file__).resolve().parent

DIR_DATOS = _AQUI.parent.parent / "data"
DIR_DATOS.mkdir(exist_ok=True)
RUTA_DB = DIR_DATOS / "ordenes.db"

_SQL_ORDENES = (_AQUI / "sql" / "ordenes.sql").read_text(encoding="utf-8")
_SQL_VIGILANCIAS = (_AQUI / "sql" / "vigilancias.sql").read_text(encoding="utf-8")

# Columnas añadidas después de la primera versión: se agregan a las bases ya existentes (migración).
_COLUMNAS_NUEVAS_ORDENES = tuple(tuple(c) for c in json.loads((_AQUI / "sql" / "columnas_nuevas.json").read_text(encoding="utf-8")))


_DB_PREPARADA: Path | None = None   # ruta de la base ya inicializada en este proceso
_DB_LOCK = threading.Lock()


def _conectar() -> sqlite3.Connection:
    global _DB_PREPARADA
    con = sqlite3.connect(RUTA_DB, timeout=10)
    con.row_factory = sqlite3.Row
    if _DB_PREPARADA != RUTA_DB:  # las tablas se crean una sola vez, no en cada consulta
        with _DB_LOCK:
            try:
                con.execute("PRAGMA journal_mode=WAL")  # lecturas y escrituras no se bloquean entre sí
            except sqlite3.OperationalError:
                pass  # otra conexión la usa ahora mismo: se queda en el modo actual
            con.execute(_SQL_ORDENES)
            existentes = {fila[1] for fila in con.execute("PRAGMA table_info(ordenes)")}
            for nombre, definicion in _COLUMNAS_NUEVAS_ORDENES:   # bases creadas antes de estas columnas
                if nombre not in existentes:
                    con.execute(f"ALTER TABLE ordenes ADD COLUMN {nombre} {definicion}")
            con.execute(_SQL_VIGILANCIAS)
            con.execute("CREATE TABLE IF NOT EXISTS estado (clave TEXT PRIMARY KEY, valor TEXT)")
            con.commit()
            _DB_PREPARADA = RUTA_DB
    return con


def _ejecutar(sql: str, params: tuple = ()) -> int:
    with closing(_conectar()) as con:
        with con:
            return con.execute(sql, params).rowcount


def _consultar(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    with closing(_conectar()) as con:
        return [dict(f) for f in con.execute(sql, params).fetchall()]


def _ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _insertar(**campos: Any) -> str:
    id_ = uuid.uuid4().hex[:8]
    ahora = datetime.now()
    base = {
        "id": id_,
        "creada": ahora.isoformat(timespec="seconds"),
        "expira": (ahora + timedelta(minutes=LIMITES.vigencia_propuesta_min)).isoformat(timespec="seconds"),
    }
    base.update(campos)
    columnas = ", ".join(base)
    marcas = ", ".join("?" for _ in base)
    _ejecutar(f"INSERT INTO ordenes ({columnas}) VALUES ({marcas})", tuple(base.values()))
    return id_


def kill_switch_activo() -> bool:
    filas = _consultar("SELECT valor FROM estado WHERE clave = 'kill_switch'")
    return bool(filas) and filas[0]["valor"] == "1"


def set_kill_switch(activo: bool) -> None:
    _ejecutar(
        "INSERT INTO estado (clave, valor) VALUES ('kill_switch', ?) "
        "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
        ("1" if activo else "0",),
    )
