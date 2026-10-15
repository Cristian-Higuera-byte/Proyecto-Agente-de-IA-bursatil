"""CSS de la barra superior y de la campana de notificaciones (vive en estilos.css)."""
from pathlib import Path

from componentes_plataforma._estaticos import estilos

CSS = estilos(Path(__file__).parent / "estilos.css")
