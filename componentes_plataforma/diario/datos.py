"""Opciones de las notas del Diario (viven en datos.json) y paleta P&J."""
from pathlib import Path

from componentes_plataforma._estaticos import datos_json

_D = datos_json(Path(__file__).parent / "datos.json")
ESTRATEGIAS = list(_D["estrategias"])
EMOCIONES = list(_D["emociones"])

# Paleta (P&J): verde #3fb950, rojo #f85149, azul #58a6ff, naranja #ff8f00.
UP, DN, AZ, NA, TX, GR = "#3fb950", "#f85149", "#58a6ff", "#ff8f00", "#e6edf3", "#8b949e"
