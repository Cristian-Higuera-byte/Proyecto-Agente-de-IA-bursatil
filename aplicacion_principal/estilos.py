"""CSS global de la plataforma (tema oscuro tipo terminal de trading); vive en estilos.css.
Se entrega con la misma sangría que tenía dentro del antiguo app.py, así el HTML que recibe Streamlit es idéntico."""
import textwrap
from pathlib import Path

from componentes_plataforma._estaticos import texto

_DIR = Path(__file__).parent


def css_global() -> str:
    return "\n    <style>\n" + textwrap.indent(texto(_DIR / "estilos.css"), " " * 8) + "    </style>\n"


def html_pantalla_carga() -> str:
    """Overlay a pantalla completa de la primera entrada (pantalla_carga.html)."""
    return "\n" + textwrap.indent(texto(_DIR / "pantalla_carga.html"), " " * 8) + "    "
