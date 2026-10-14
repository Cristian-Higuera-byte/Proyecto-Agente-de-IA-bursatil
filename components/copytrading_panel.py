"""Vista "Copy trading" (datos simulados). El código vive en components/copytrading/ (datos, gráficos, tarjeta, ficha,
panel y estilos); este archivo se mantiene para que `from components.copytrading_panel import renderizar_panel_copytrading`
(app.py) siga funcionando."""
from components.copytrading import renderizar_panel_copytrading

__all__ = ["renderizar_panel_copytrading"]
