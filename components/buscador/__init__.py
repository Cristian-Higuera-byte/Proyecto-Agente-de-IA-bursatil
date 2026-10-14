"""
Paquete del buscador de activos. API pública:
  - abrir_buscador / render_buscador (patrón bandera + render en app.py).
  - _agregar_a_watchlist: lo reutiliza mercados_panel.py.
La lógica/datos viven en datos.py y el modal en dialogo.py.
"""
from .dialogo import abrir_buscador, render_buscador
from .datos import _agregar_a_watchlist, cargar_simbolos_broker

__all__ = ["abrir_buscador", "render_buscador", "_agregar_a_watchlist",
           "cargar_simbolos_broker"]
