"""CSS del carrusel y de las tarjetas clicables de noticias (vive en estilos.css)."""
from pathlib import Path

from componentes_plataforma._estaticos import estilos

CSS_CARRUSEL = estilos(Path(__file__).parent / "estilos.css")
