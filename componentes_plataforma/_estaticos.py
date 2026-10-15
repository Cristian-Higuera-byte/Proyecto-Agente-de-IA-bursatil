"""Lectura de los archivos estáticos (CSS, JSON) que viven junto a cada componente.

Cada componente separado (profundidad_mercado/, favoritos/, copytrading/…) guarda su CSS en `estilos.css` y sus datos
en `.json`. Aquí se leen una sola vez y se vuelven a leer solos si el archivo cambia en disco (como el
ensamblador del gráfico), así que editar un CSS se ve al recargar la página sin reiniciar Streamlit.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_cache: dict[str, tuple[int, Any]] = {}


def _leer(ruta: Path, convertir) -> Any:
    marca = ruta.stat().st_mtime_ns
    guardado = _cache.get(str(ruta))
    if guardado and guardado[0] == marca:
        return guardado[1]
    valor = convertir(ruta.read_text(encoding="utf-8"))
    _cache[str(ruta)] = (marca, valor)
    return valor


def texto(ruta: str | Path) -> str:
    """Contenido de un archivo de texto."""
    return _leer(Path(ruta), lambda t: t)


def datos_json(ruta: str | Path) -> Any:
    """Contenido de un archivo JSON ya convertido (listas, diccionarios…)."""
    return _leer(Path(ruta), json.loads)


def estilos(ruta: str | Path) -> str:
    """CSS de un archivo `.css` envuelto en <style>, listo para `st.html(...)` o `st.markdown(..., unsafe_allow_html=True)`."""
    return "\n<style>\n" + texto(ruta) + "</style>\n"
