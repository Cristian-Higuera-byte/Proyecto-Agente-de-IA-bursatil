"""Accesos rápidos y promociones de la vista Inicio (viven en datos.json)."""
from pathlib import Path

from componentes_plataforma._estaticos import datos_json

_D = datos_json(Path(__file__).parent / "datos.json")

# (ícono Material, color, título, subtítulo, destino o None)
ACCIONES = [tuple(a) for a in _D["acciones"]]
# (clase, ícono Material, color, título, descripción)
PROMOS = [tuple(p) for p in _D["promos"]]
