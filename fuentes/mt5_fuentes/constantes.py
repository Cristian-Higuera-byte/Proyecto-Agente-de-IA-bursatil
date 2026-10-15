"""Tiempos de conexión, temporalidades, funciones de MT5 permitidas (solo lectura) y alias de símbolos (datos.json)."""
import json
from pathlib import Path

_D = json.loads((Path(__file__).parent / "datos.json").read_text(encoding="utf-8"))

_TIMEOUT_MS = 10_000
_REINTENTO_S = 15
_TTL_SIMBOLOS_S = 600
_TTL_RUTAS_S = 300
_TTL_OFFSET_S = 300
_MAX_RUTAS = 3

TIMEFRAMES = dict(_D["timeframes"])

_FUNCIONES_PERMITIDAS = frozenset(_D["funciones_permitidas"])

_ALIAS = {k: list(v) for k, v in _D["alias"].items()}
