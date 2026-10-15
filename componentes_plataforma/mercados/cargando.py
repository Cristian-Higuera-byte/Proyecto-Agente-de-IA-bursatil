"""Indicador "cargando" de la ficha. Se muestra EN EL NAVEGADOR en el mismo instante del clic (un st.spinner de
Python recién aparecería cuando el servidor ya va a mitad del rerun) y se quita solo cuando el modal de la
ficha está en el DOM. El script vive en estatico/cargando.js."""
from pathlib import Path

from componentes_plataforma._estaticos import texto

JS_CARGANDO = "\n<script>\n" + texto(Path(__file__).parent / "estatico" / "cargando.js") + "</script>\n"
