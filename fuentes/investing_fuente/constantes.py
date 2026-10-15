"""Feeds RSS de Investing.com, aviso de la fuente y cabeceras HTTP (datos.json)."""
import json
from pathlib import Path

_D = json.loads((Path(__file__).parent / "datos.json").read_text(encoding="utf-8"))

FEEDS: dict[str, str] = dict(_D["feeds"])

AVISO_FUENTE = _D["aviso_fuente"]

HEADERS = dict(_D["headers"])
