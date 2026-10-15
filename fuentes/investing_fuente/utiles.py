"""Utilidades de limpieza de los textos de las noticias."""
from __future__ import annotations

import re
from typing import Any


def _limpiar_html(texto: str) -> str:
    """Elimina etiquetas HTML e inconsistencias de formato en los resúmenes."""
    if not texto:
        return ""
    sin_html = re.sub(r"<[^>]+>", "", texto)
    return " ".join(sin_html.split()).strip()


def _sin_nulos(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}
