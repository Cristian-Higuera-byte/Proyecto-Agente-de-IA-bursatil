"""Panel de noticias. El código vive en componentes_plataforma/noticias/ (panel, secciones, modal, RSS, datos y estilos);
este archivo se mantiene para que el `from componentes_plataforma.noticias_panel import renderizar_panel_noticias` de aplicacion.py
siga funcionando."""
from componentes_plataforma.noticias import renderizar_panel_noticias

__all__ = ["renderizar_panel_noticias"]
