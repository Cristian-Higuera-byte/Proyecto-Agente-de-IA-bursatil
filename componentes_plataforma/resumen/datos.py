"""Acentos de las tarjetas KPI y periodos de la curva (viven en datos.json)."""
from pathlib import Path

from componentes_plataforma._estaticos import datos_json

_D = datos_json(Path(__file__).parent / "datos.json")

# clave -> (acento, icono, fondo icono, color icono)
ACC = {k: tuple(v) for k, v in _D["acentos"].items()}
PERIODOS = dict(_D["periodos"])
