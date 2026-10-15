"""Funciones y constantes auxiliares de las herramientas (sin registrar nada)."""
from __future__ import annotations

from pathlib import Path

from herramientas_agente.base import cargar_json


_DATOS = cargar_json(Path(__file__).parent / "datos.json")


CATEGORIAS = ("economia", "forex", "mercados")


# Palabras (minúsculas) que delatan un evento macro de alto impacto en un titular.
_EVENTOS = tuple(_DATOS["_EVENTOS"])


# Palabras que vinculan un titular con una divisa.
_DIVISAS = {k: tuple(v) for k, v in _DATOS["_DIVISAS"].items()}
