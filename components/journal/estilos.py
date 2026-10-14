"""CSS de la vista Diario (vive en estilos.css)."""
from pathlib import Path

from components._estaticos import estilos

CSS = estilos(Path(__file__).parent / "estilos.css")
