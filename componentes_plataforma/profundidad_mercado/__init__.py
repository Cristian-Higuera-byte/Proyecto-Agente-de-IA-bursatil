"""Panel de PROFUNDIDAD DE MERCADO (DOM), estilo XM. Se abre desde el rail de iconos de la derecha (panel_riel.py).

    panel.py     renderizar_panel_dom(): cabecera + escalera que se refresca sola
    escalera.py  HTML de la escalera (profundidad real del bróker o vista demostrativa)
    estilos.css  estilos del panel
"""
from componentes_plataforma.profundidad_mercado.panel import renderizar_panel_dom

__all__ = ["renderizar_panel_dom"]
