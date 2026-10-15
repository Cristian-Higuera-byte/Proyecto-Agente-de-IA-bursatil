"""Envoltorio del módulo MetaTrader5 que solo deja pasar consultas (el agente es de SOLO LECTURA)."""
from __future__ import annotations

from typing import Any

from fuentes.mt5_fuentes.constantes import _FUNCIONES_PERMITIDAS
from fuentes.mt5_fuentes.errores import OperacionNoPermitida


class _SoloLectura:
    """Envuelve el módulo MetaTrader5 y solo deja pasar consultas."""

    def __init__(self, modulo: Any) -> None:
        object.__setattr__(self, "_modulo", modulo)

    def __getattr__(self, nombre: str) -> Any:
        if nombre.startswith("__"):
            raise AttributeError(nombre)
        if nombre in _FUNCIONES_PERMITIDAS or nombre.isupper():
            return getattr(self._modulo, nombre)
        raise OperacionNoPermitida(f"Operación no permitida: '{nombre}'. El agente es de solo lectura.")

    def __setattr__(self, nombre: str, valor: Any) -> None:
        raise OperacionNoPermitida("El módulo MT5 es de solo lectura.")
