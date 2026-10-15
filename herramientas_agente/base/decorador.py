"""Decorador @herramienta: registra una función Python como herramienta del agente."""
from __future__ import annotations

from typing import Any, Callable

from herramientas_agente.base.registro import REGISTRO, Herramienta, RegistroHerramientas


def herramienta(
    descripcion: str,
    parametros: dict[str, Any] | None = None,
    requeridos: list[str] | None = None,
    nombre: str | None = None,
    registro: RegistroHerramientas = REGISTRO,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorador que registra una función como herramienta del agente."""

    def decorador(funcion: Callable[..., Any]) -> Callable[..., Any]:
        esquema = {
            "type": "object",
            "properties": parametros or {},
            "required": requeridos or [],
        }
        registro.registrar(Herramienta(nombre or funcion.__name__, descripcion, esquema, funcion))
        return funcion

    return decorador
