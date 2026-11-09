# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ------------------------------------ INICIO Piña y Jara navegacion .PY --------------------------------
# -------------------------------------------------------------------------------------------------------

"""Navegación sin recargar entre la portada, el inicio de sesión, el registro y «Olvidé mi contraseña».

Los enlaces entre esas pantallas (`?acceso=entrar`, `?acceso=crear`, `./`...) recargaban toda la página y dejaban ver el esqueleto gris de Streamlit al volver a arrancar.
El componente de estatico/navegacion.js intercepta esos clics y avisa a Python; aquí se traduce el destino a parámetros de la dirección y Streamlit dibuja la pantalla
nueva en la misma sesión, sin recarga. Mientras se dibuja, el contenido se oculta (estatico/navegacion.css) para no mostrar la pantalla vieja sin sus estilos ni la nueva a
medias. Un clic con Ctrl, Mayús o el botón medio sigue abriendo el enlace normal.
"""
from pathlib import Path
from urllib.parse import parse_qs

import streamlit as st

from componentes_plataforma._estaticos import texto

# Clave del componente en `st.session_state` y carpeta del script.
_CLAVE = "pj_navegacion_acceso"
_ESTATICO = Path(__file__).parent / "estatico"

# El componente se declara una sola vez al importar el módulo (no dentro de la función, para no registrarlo dos veces).
_COMPONENTE = st.components.v2.component("pj_navegacion_acceso", html="<span></span>", css=texto(_ESTATICO / "navegacion.css") + "\n",
                                         js=texto(_ESTATICO / "navegacion.js") + "\n", isolate_styles=False)


# TITULO AL NAVEGAR

def _al_navegar() -> None:
    """Cambia los parámetros de la dirección según el enlace pulsado (`?acceso=crear&plan=pro` → acceso y plan; `./` → ninguno, la portada).

    Solo se aceptan las claves `acceso` y `plan`; cualquier otra se ignora. Streamlit vuelve a ejecutar la página con la dirección nueva."""
    destino = str((st.session_state.get(_CLAVE) or {}).get("destino") or "")
    if not destino:
        return
    pedidos = parse_qs(destino[1:] if destino.startswith("?") else "")
    st.query_params.clear()
    for clave in ("acceso", "plan"):
        if pedidos.get(clave):
            st.query_params[clave] = pedidos[clave][0]


# TITULO MONTAR

def montar() -> None:
    """Pone en la pantalla el componente que evita la recarga al pasar entre las pantallas de acceso; va una vez, antes de dibujarlas. No devuelve nada."""
    _COMPONENTE(key=_CLAVE, on_destino_change=_al_navegar)


# -------------------------------------------------------------------------------------------------------
# ------------------------------------- FIN Piña y Jara navegacion .PY ----------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
