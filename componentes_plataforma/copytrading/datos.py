"""Datos SIMULADOS de copy trading: las estrategias están en estrategias.json (editable sin tocar código)."""
from pathlib import Path

from componentes_plataforma import _estaticos

ESTRATEGIAS = _estaticos.datos_json(Path(__file__).parent / "estrategias.json")

CATEGORIAS = ["Cualquiera", "Forex", "Índices", "Criptomonedas", "Materias primas", "Algorítmico"]
TABS = ["Destacadas", "Mejores resultados", "Ratio de victorias alto", "Fondos propios altos",
        "Riesgo bajo", "Drawdown bajo", "Comisiones bajas", "Más populares"]
ORDEN = {
    "Destacadas": lambda e: -e["rent"],
    "Mejores resultados": lambda e: -e["rent"],
    "Ratio de victorias alto": lambda e: -e["win"],
    "Fondos propios altos": lambda e: -e["fondos"],
    "Riesgo bajo": lambda e: {"bajo": 0, "medio": 1, "alto": 2}[e["riesgo"]],
    "Drawdown bajo": lambda e: e["drawdown"],
    "Comisiones bajas": lambda e: e["comision"],
    "Más populares": lambda e: -e["inversores"],
}
RIESGO_CLS = {"bajo": "rb", "medio": "rm", "alto": "ra"}
RIESGO_TXT = {"bajo": "Riesgo bajo", "medio": "Riesgo medio", "alto": "Riesgo alto"}


def por_id(eid):
    return next((e for e in ESTRATEGIAS if e["id"] == eid), None)
