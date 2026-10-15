"""
Paquete de la barra lateral de navegación. API pública: `renderizar_barra_navegacion`
(la importa aplicacion.py). La lógica y los datos viven en barra.py; el CSS y el JS del toggle,
en estatico/ (barra_lateral.css / barra_lateral.js).
"""
from .barra import ITEMS, ANCHO_COLAPSADO, ANCHO_EXPANDIDO, renderizar_barra_navegacion

__all__ = ["renderizar_barra_navegacion", "ITEMS", "ANCHO_COLAPSADO", "ANCHO_EXPANDIDO"]
