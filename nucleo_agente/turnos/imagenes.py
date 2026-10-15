"""Imágenes que una herramienta guardó en disco, a partir de su resultado."""
from __future__ import annotations

import json
import os
from typing import Any

_EXT_IMAGEN = (".png", ".jpg", ".jpeg", ".webp")


def _buscar_rutas_imagen(dato: Any, rutas: list) -> None:
    """Busca de forma recursiva el campo 'archivo_guardado' (imagen en disco) en un resultado."""
    if isinstance(dato, dict):
        ruta = dato.get("archivo_guardado")
        if isinstance(ruta, str) and ruta.lower().endswith(_EXT_IMAGEN) and os.path.isfile(ruta):
            if ruta not in rutas:
                rutas.append(ruta)
        for valor in dato.values():
            if isinstance(valor, (dict, list)):
                _buscar_rutas_imagen(valor, rutas)
    elif isinstance(dato, list):
        for valor in dato:
            _buscar_rutas_imagen(valor, rutas)


def imagenes_de_resultado(resultado: Any) -> list:
    """Imágenes que una herramienta guardó en disco, a partir de su resultado (JSON o dict)."""
    try:
        datos = json.loads(resultado) if isinstance(resultado, str) else resultado
    except (TypeError, ValueError):
        return []
    rutas: list = []
    _buscar_rutas_imagen(datos, rutas)
    return rutas
