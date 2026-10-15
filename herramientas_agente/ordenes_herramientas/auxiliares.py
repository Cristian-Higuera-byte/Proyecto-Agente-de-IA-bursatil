"""Funciones y constantes auxiliares de las herramientas (sin registrar nada)."""
from __future__ import annotations

from typing import Any


def _a_numero(valor: Any) -> Any:
    """Los LLM a veces envían números como texto; se convierten si es posible."""
    if isinstance(valor, str):
        try:
            return float(valor.replace(",", "."))
        except ValueError:
            return valor
    return valor
