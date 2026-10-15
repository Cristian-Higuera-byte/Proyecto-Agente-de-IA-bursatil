"""Medidas del rail y sus botones (botones.json)."""
from pathlib import Path

from componentes_plataforma._estaticos import datos_json

RAIL = 50        # ancho del rail (px) — angosto, como una barra de iconos
PANEL = 312      # ancho del panel desplegado (px)
TOP = 62         # alto de la barra superior (ajústalo si el panel queda alto/bajo)

# (icono material, id del panel, nombre del tooltip)
BOTONES = [tuple(b) for b in datos_json(Path(__file__).parent / "botones.json")]
