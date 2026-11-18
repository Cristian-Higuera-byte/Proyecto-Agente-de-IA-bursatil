# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ------------------------------------ INICIO Piña y Jara panel .PY -------------------------------------
# -------------------------------------------------------------------------------------------------------

"""Portada pública de la plataforma: lo primero que ve quien aún no inició sesión.

`renderizar_portada()` dibuja la página completa (barra, héroe con captura real, beneficios, gráficos, agente, mercados, noticias, herramientas, pasos, planes, preguntas, cierre y pie). Los botones llevan a los formularios
de acceso con `?acceso=entrar` o `?acceso=crear` (ver acceso/pantalla.py). Es una página informativa: no consulta datos de cuentas ni del bróker.
"""
from pathlib import Path

import streamlit as st

from componentes_plataforma._estaticos import estilos
import configuracion
from componentes_plataforma.portada import secciones, secciones_azul

# CSS de la portada (los 8 cortes de pantalla de la empresa); se vuelve a leer solo si el archivo cambia en disco.
_CSS = Path(__file__).parent / "estilos.css"
_CSS_AZUL = Path(__file__).parent / "estilos_azul.css"
# Cada cuántos segundos se refresca la sección de mercados.
REFRESCO_S = 5


# TITULO MERCADOS EN VIVO

@st.fragment(run_every=f"{REFRESCO_S}s")
def _cinta_en_vivo() -> None:
    """Cinta de precios del tema azul como fragmento: se vuelve a dibujar sola con las cotizaciones más recientes de la caché de `datos.py` (sin peticiones nuevas a Capital.com)."""
    st.html(secciones_azul.cinta())



@st.fragment(run_every=f"{REFRESCO_S}s")
def _mercados_en_vivo() -> None:
    """Sección «Mercados» como fragmento: se vuelve a dibujar sola cada pocos segundos (solo ella, no la página) para mostrar los precios más recientes de la caché de `datos.py`.

    Los visitantes solo leen la caché del servidor, así que refrescar no genera peticiones a Capital.com."""
    st.html(secciones.activos())


# TITULO RENDERIZAR PORTADA

def renderizar_portada() -> None:
    """Dibuja la portada completa en la página de Streamlit. No recibe parámetros ni devuelve nada.

    Inyecta el CSS (que además oculta el relleno de Streamlit para usar todo el ancho) y el HTML de cada sección, en orden de arriba a abajo; la sección de mercados es un fragmento que se refresca sola."""
    st.html(estilos(_CSS))
    azul = bool(getattr(configuracion, "TEMA_AZUL", True))
    if azul:
        st.html(estilos(_CSS_AZUL))     # diseño azul propuesto por el cliente (se apaga con TEMA_AZUL = False en configuracion.py)
    st.html("".join(f() for f in (secciones.barra, secciones.heroe)))
    if azul:
        _cinta_en_vivo()
        st.html(secciones_azul.categorias() + secciones_azul.banner())
    st.html("".join(f() for f in (secciones.porque, secciones.graficos, secciones.agente)))
    _mercados_en_vivo()
    st.html("".join(f() for f in (secciones.noticias, secciones.herramientas, secciones.pasos, secciones.planes, secciones.preguntas)))
    if azul:
        st.html(secciones_azul.confianza())
    st.html("".join(f() for f in (secciones.cierre, secciones.pie)))


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
