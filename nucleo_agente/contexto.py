"""Contexto de la consulta en curso (quién la hace).

NOMBRE DEL ARCHIVO: nucleo_agente/contexto.py

Las herramientas del agente son funciones normales y no reciben al usuario como argumento. Mientras
nucleo_agente/turnos.py ejecuta una consulta en su hilo, fija aquí el usuario; las herramientas que lo
necesitan (p. ej. crear una vigilancia automática) lo leen con usuario_actual(). Es por hilo
(ContextVar), así que consultas de usuarios distintos no se mezclan.
"""

from __future__ import annotations

import contextvars

_USUARIO: contextvars.ContextVar[str] = contextvars.ContextVar("usuario_id", default="local")


def fijar_usuario(usuario_id: str) -> None:
    _USUARIO.set(str(usuario_id or "local"))


def usuario_actual() -> str:
    return _USUARIO.get()
