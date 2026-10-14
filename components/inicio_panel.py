"""Panel de Inicio. El código vive en components/inicio/ (cuenta, posiciones, historial, modal, datos y
estilos); este archivo se mantiene para que el `from components.inicio_panel import renderizar_panel_inicio`
de app.py siga funcionando."""
from components.inicio import renderizar_panel_inicio

__all__ = ["renderizar_panel_inicio"]
