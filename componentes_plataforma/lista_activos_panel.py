"""Lista de activos. El código vive en componentes_plataforma/lista_activos/ (panel, fila, acciones y estilos); este archivo
se mantiene para que el `from componentes_plataforma.lista_activos_panel import renderizar_watchlist` de aplicacion.py siga funcionando."""
from componentes_plataforma.lista_activos import ALTURA_LISTA, renderizar_watchlist

__all__ = ["renderizar_watchlist", "ALTURA_LISTA"]
