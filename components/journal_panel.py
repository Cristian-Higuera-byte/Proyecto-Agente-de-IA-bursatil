"""Vista Diario. El código vive en components/journal/ (tabla, ficha, mini-gráfico, datos y estilos); este
archivo se mantiene para que el `from components.journal_panel import renderizar_panel_journal` de app.py
siga funcionando."""
from components.journal import renderizar_panel_journal

__all__ = ["renderizar_panel_journal"]
