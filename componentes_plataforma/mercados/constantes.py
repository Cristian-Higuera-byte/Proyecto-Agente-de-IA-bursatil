"""Catálogo de instrumentos, resumen, órdenes y colores de la página Mercados (los datos viven en datos.json)."""
from pathlib import Path

from componentes_plataforma._estaticos import datos_json

_D = datos_json(Path(__file__).parent / "datos.json")

# {categoría: [(candidatos, nombre)]}. El primer candidato que exista en el bróker se usa.
CATALOGO = {cat: [(tuple(c), n) for c, n in items] for cat, items in _D["catalogo"].items()}

# "Pulso del mercado": la referencia más seguida de cada mercado
# (categoría, índice dentro del catálogo, qué representa)
RESUMEN = [tuple(x) for x in _D["resumen"]]

ORDENES = list(_D["ordenes"])

# Columnas de la tabla — cabecera y filas comparten el reparto
GRID = _D["grid"]

VERDE, ROJO, GRIS = "#3fb950", "#f85149", "#8b949e"
