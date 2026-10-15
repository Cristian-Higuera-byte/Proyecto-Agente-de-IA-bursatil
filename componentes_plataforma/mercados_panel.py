"""Página Mercados. El código vive en componentes_plataforma/mercados/ (panel, secciones, ficha, gráfico, piezas, datos del
bróker, catálogo JSON y estilos); este archivo se mantiene para que el
`from componentes_plataforma.mercados_panel import renderizar_panel_mercados` de aplicacion.py siga funcionando."""
from componentes_plataforma.mercados import renderizar_panel_mercados

__all__ = ["renderizar_panel_mercados"]
