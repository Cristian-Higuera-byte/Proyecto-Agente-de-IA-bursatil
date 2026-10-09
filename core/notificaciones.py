"""Notificaciones del dashboard (campana de la barra superior).

NOMBRE DEL ARCHIVO: core/notificaciones.py

Almacén en memoria del proceso, por usuario. No usa Streamlit, así que lo puede escribir un hilo
en segundo plano (core/turnos.py) y leer la barra superior (components/top_navbar.py).

Las notificaciones se pierden si se reinicia el servidor; es un aviso, no un registro de auditoría
(la auditoría de las órdenes ya está en data/ordenes.db).
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

MAX_POR_USUARIO = 50

_LOCK = threading.Lock()
_DATOS: dict[str, list[dict[str, Any]]] = {}


def agregar(
    usuario_id: str,
    titulo: str,
    texto: str = "",
    tipo: str = "agente",        # agente | orden | error
    ref: str | None = None,      # id del turno que la originó
    leida: bool = False,
) -> dict[str, Any]:
    nueva = {
        "id": uuid.uuid4().hex[:8], "titulo": titulo, "texto": texto, "tipo": tipo,
        "ref": ref, "leida": leida, "creada": time.time(),
    }
    with _LOCK:
        lista = _DATOS.setdefault(usuario_id, [])
        lista.insert(0, nueva)
        del lista[MAX_POR_USUARIO:]
    return dict(nueva)


def listar(usuario_id: str, limite: int = 10) -> list[dict[str, Any]]:
    with _LOCK:
        return [dict(n) for n in _DATOS.get(usuario_id, [])[:limite]]


def no_leidas(usuario_id: str) -> int:
    with _LOCK:
        return sum(1 for n in _DATOS.get(usuario_id, []) if not n["leida"])


def ultima_id(usuario_id: str) -> str | None:
    """Id de la notificación más reciente (sirve para detectar que llegó una nueva)."""
    with _LOCK:
        lista = _DATOS.get(usuario_id, [])
        return lista[0]["id"] if lista else None


def marcar_leidas(usuario_id: str, ref: str | None = None) -> None:
    """Marca como leídas todas las del usuario, o solo las de un turno (`ref`)."""
    with _LOCK:
        for n in _DATOS.get(usuario_id, []):
            if ref is None or n["ref"] == ref:
                n["leida"] = True


def limpiar(usuario_id: str) -> None:
    with _LOCK:
        _DATOS.pop(usuario_id, None)
