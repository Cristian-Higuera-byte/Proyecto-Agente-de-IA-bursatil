"""CSS de la lista de activos (vive en estilos.css). Termina con la marca .wl-css que el propio CSS usa para
ocultar el contenedor del bloque de estilos."""
from pathlib import Path

from componentes_plataforma._estaticos import estilos

CSS = estilos(Path(__file__).parent / "estilos.css") + '<span class="wl-css"></span>\n'
