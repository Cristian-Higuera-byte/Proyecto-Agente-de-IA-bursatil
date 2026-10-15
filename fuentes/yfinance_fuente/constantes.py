"""Periodos e intervalos válidos de Yahoo Finance, aviso de retraso y mapas de campos (datos.json)."""
import json
from pathlib import Path

_D = json.loads((Path(__file__).parent / "datos.json").read_text(encoding="utf-8"))

PERIODOS = tuple(_D["periodos"])
INTERVALOS = tuple(_D["intervalos"])

AVISO_RETRASO = _D["aviso_retraso"]

# Fundamentales (Ticker.info): clave de salida -> campo de Yahoo
_CAMPOS_TEXTO = dict(_D["campos_texto"])
_CAMPOS_NUM = dict(_D["campos_num"])

# Estados financieros: tipo -> (atributo anual, atributo trimestral, filas clave)
_ESTADOS = {k: (v[0], v[1], tuple(v[2])) for k, v in _D["estados"].items()}
