"""Vista Diario. El código vive en componentes_plataforma/diario/ (tabla, ficha, mini-gráfico, datos y estilos); este
archivo se mantiene para que el `from componentes_plataforma.diario_panel import renderizar_panel_journal` de aplicacion.py
siga funcionando."""
from componentes_plataforma.diario import renderizar_panel_journal

__all__ = ["renderizar_panel_journal"]
