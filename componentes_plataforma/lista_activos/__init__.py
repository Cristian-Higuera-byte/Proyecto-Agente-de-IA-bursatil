"""
componentes_plataforma/lista_activos
------------------------
Lista de activos (watchlist) del panel izquierdo: tarjetas con ícono, precio y variación en vivo (feed),
selección de activo, favoritos y quitar de la lista.
Archivos: panel.py, fila.py, acciones.py, estilos.py + estilos.css.
"""
from componentes_plataforma.lista_activos.panel import ALTURA_LISTA, renderizar_watchlist

__all__ = ["renderizar_watchlist", "ALTURA_LISTA"]
