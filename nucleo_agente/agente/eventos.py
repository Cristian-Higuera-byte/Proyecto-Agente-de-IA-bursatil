"""Evento que emite el agente mientras responde."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EventoAgente:
    """tipo: 'razonamiento' | 'texto' | 'herramienta' | 'resultado' | 'fin'"""

    tipo: str
    texto: str = ""
    datos: dict[str, Any] = field(default_factory=dict)
