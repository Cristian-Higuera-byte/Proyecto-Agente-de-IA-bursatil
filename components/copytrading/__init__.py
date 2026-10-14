"""Vista "Copy trading" (datos simulados).

    datos.py        estrategias (estrategias.json), categorías, pestañas de orden
    graficos.py     sparkline, dona y avatar en SVG
    tarjeta.py      tarjeta del listado
    ficha.py        ficha de detalle de una estrategia
    panel.py        renderizar_panel_copytrading(): listado + detalle
    estilos.css     estilos de la vista
"""
from components.copytrading.panel import renderizar_panel_copytrading

__all__ = ["renderizar_panel_copytrading"]
