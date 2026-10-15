"""Arma el HTML del gráfico a partir de los fragmentos de `estatico/`.

`estatico/esqueleto.html` es el documento completo; cada línea `@@ruta` se reemplaza por el contenido de
ese fragmento (css/, html/ o js/). Todos los fragmentos de JS comparten UN mismo bloque (la función
`iniciar()`), por eso el orden del esqueleto importa: no cambies el orden de los `@@js/...` sin probar.

El resultado se guarda en memoria y se rehace solo si algún fragmento cambia en disco.
"""
from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path

_DIR = Path(__file__).parent / "estatico"
_INCLUIR = re.compile(r"^@@(\S+)\n", re.MULTILINE)
_cache: dict = {"firma": None, "plantilla": ""}


def _firma() -> tuple:
    return tuple((str(p), p.stat().st_mtime_ns) for p in sorted(_DIR.rglob("*")) if p.is_file())


def plantilla() -> str:
    """HTML completo del gráfico, con los marcadores __X__ todavía sin sustituir."""
    firma = _firma()
    if _cache["firma"] != firma:
        esqueleto = (_DIR / "esqueleto.html").read_text(encoding="utf-8")
        _cache["plantilla"] = _INCLUIR.sub(lambda m: (_DIR / m.group(1)).read_text(encoding="utf-8"), esqueleto)
        _cache["firma"] = firma
    return _cache["plantilla"]


def html_grafico(simbolo: str, api_url: str, digits: int, pip: float, posiciones_js: str, activos_json: str = "[]") -> str:
    """HTML listo para `components.html` con los datos del símbolo."""
    return (
        plantilla()
        .replace("__SIMBOLO_HTML__", escape(simbolo))
        .replace("__SIMBOLO_JS__", json.dumps(simbolo))
        .replace("__API_URL_JS__", json.dumps(api_url))
        .replace("__DIGITS__", str(digits))
        .replace("__PIP__", json.dumps(pip))
        .replace("__ACTIVOS_JSON__", activos_json)   # lista de activos del selector de pantalla completa
        .replace("__POSICIONES_JS__", posiciones_js)   # líneas de posición, SL/TP y órdenes
    )
