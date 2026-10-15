"""Argumentos de las llamadas a herramientas (JSON del modelo)."""
from __future__ import annotations

import json
from typing import Any


def _parsear_argumentos(raw: str) -> tuple[dict[str, Any], str | None]:
    if not raw:
        return {}, None
    try:
        datos = json.loads(raw)
        if not isinstance(datos, dict):
            return {}, f"Los argumentos deben ser un objeto JSON, llegó: {raw!r}"
        return datos, None
    except json.JSONDecodeError:
        return {}, f"Argumentos con JSON inválido: {raw!r}"
