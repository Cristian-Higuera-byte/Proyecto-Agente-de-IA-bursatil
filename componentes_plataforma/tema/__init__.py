# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# --------------------------------------- INICIO Piña y Jara __init__ .PY -------------------------------
# -------------------------------------------------------------------------------------------------------

"""Tema azul de la plataforma (prueba de cambio de colores pedida por el cliente).

`instalar()` se llama una vez al empezar la página: envuelve `st.markdown`, `st.html` y `components.html` para que todo texto con colores (CSS, HTML y el JavaScript del gráfico)
pase por `paleta.aplicar` y salga con la paleta azul, y `css_extra()` entrega el fondo degradado y otros detalles del tema. No se edita ningún archivo de componentes: el tema vive
aquí y se apaga poniendo `TEMA_AZUL = False` en `configuracion.py` (la plataforma vuelve a verse como antes, sin tocar nada más).

    paleta.py     tablas de colores viejo -> nuevo y `aplicar()`
    estilos.css   fondo con degradados azules, selección de texto y barras de desplazamiento del tema
"""
import functools
from pathlib import Path

import streamlit as st

import configuracion
from componentes_plataforma._estaticos import texto
from componentes_plataforma.tema.paleta import aplicar

_CSS = Path(__file__).parent / "estilos.css"
_MARCA = "_pj_tema_azul_instalado"


# TITULO ACTIVO

def activo() -> bool:
    """True si el tema azul está encendido (`configuracion.TEMA_AZUL`, encendido por defecto)."""
    return bool(getattr(configuracion, "TEMA_AZUL", True))


# TITULO ENVOLVER

def _envolver(funcion, posicion: int, naranja: bool = True):
    """Devuelve `funcion` envuelta para que su argumento de texto (el que está en `posicion`, o con nombre `body`/`html`) pase por la paleta antes de enviarse al navegador.

    `naranja` dice si los naranjas de la marca pasan a azul (páginas de Streamlit) o se conservan (marcos del navegador como el gráfico, donde el naranja tiene significado propio)."""
    @functools.wraps(funcion)
    def envuelta(*args, **opciones):
        if len(args) > posicion and isinstance(args[posicion], str):
            args = args[:posicion] + (aplicar(args[posicion], naranja),) + args[posicion + 1:]
        else:
            for nombre in ("body", "html"):
                if isinstance(opciones.get(nombre), str):
                    opciones[nombre] = aplicar(opciones[nombre], naranja)
        return funcion(*args, **opciones)
    return envuelta


# TITULO INSTALAR

def instalar() -> None:
    """Pone el tema en marcha (una sola vez por proceso). Si el tema está apagado o ya se instaló, no hace nada."""
    if not activo() or getattr(st, _MARCA, False):
        return
    import streamlit.components.v1 as componentes
    from streamlit.delta_generator import DeltaGenerator
    for nombre in ("markdown", "html"):
        setattr(st, nombre, _envolver(getattr(st, nombre), 0))
        if hasattr(DeltaGenerator, nombre):
            setattr(DeltaGenerator, nombre, _envolver(getattr(DeltaGenerator, nombre), 1))
    componentes.html = _envolver(componentes.html, 0, naranja=False)
    setattr(st, _MARCA, True)


# TITULO CSS EXTRA

def css_extra() -> str:
    """CSS propio del tema (ya con los colores nuevos) listo para `st.markdown`; cadena vacía si el tema está apagado."""
    return "\n<style>\n" + texto(_CSS) + "</style>\n" if activo() else ""


# -------------------------------------------------------------------------------------------------------
# ----------------------------------------- FIN Piña y Jara __init__ .PY --------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
