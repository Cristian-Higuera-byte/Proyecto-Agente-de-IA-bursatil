"""CSS de la página Mercados y de la ficha del instrumento (vive en estilos.css)."""
from pathlib import Path

from componentes_plataforma._estaticos import estilos

CSS = estilos(Path(__file__).parent / "estilos.css")
