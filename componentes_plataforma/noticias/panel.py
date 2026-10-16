# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ------------------------------------- INICIO Piña y Jara panel .PY ------------------------------------
# -------------------------------------------------------------------------------------------------------

"""Panel de noticias estilo Investing.com: arma la página (modal de la noticia abierta + contenido que se
refresca cada 30 s)."""
from types import ModuleType
from typing import Optional

import streamlit as st

from componentes_plataforma.noticias.modal import abrir_modal
from componentes_plataforma.noticias.secciones import renderizar_contenido


def renderizar_panel_noticias(main: Optional[ModuleType] = None):
    """Dibuja la página de noticias.

    El parámetro `main` se acepta por compatibilidad con las demás páginas y no se usa. Si hay una noticia
    guardada en `st.session_state["noticia_abierta"]`, abre su modal; después pinta el contenido dentro de un
    fragmento que se vuelve a ejecutar cada 30 s. No devuelve nada."""
    # Si hay una noticia seleccionada, se abre el modal desde el flujo principal
    # (no desde un fragmento) para que funcione correctamente.
    if st.session_state.get("noticia_abierta") is not None:
        abrir_modal(st.session_state["noticia_abierta"])

    @st.fragment(run_every="30s")
    def _contenido():
        """Fragmento con auto-refresco que repinta noticia principal, carrusel y "Más noticias"."""
        renderizar_contenido()
    _contenido()


# -------------------------------------------------------------------------------------------------------
# -------------------------------------- FIN Piña y Jara panel .PY --------------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
