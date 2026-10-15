"""Carga de los esquemas de herramientas guardados en esquemas.json / datos.json de cada paquete."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def cargar_json(ruta: str | Path) -> Any:
    """Contenido de un archivo JSON (UTF-8). Los esquemas se pasan tal cual a `@herramienta(**esquema)`."""
    return json.loads(Path(ruta).read_text(encoding="utf-8"))
