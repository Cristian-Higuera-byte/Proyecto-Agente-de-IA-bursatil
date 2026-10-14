"""Chat del agente de IA. El código vive en components/chat/ (sesión, historial, turno en vivo y panel); este archivo
se mantiene para que `from components.chat_agente import renderizar_chat_agente` (central_panel.py, app.py) siga
funcionando."""
from components.chat import renderizar_chat_agente

__all__ = ["renderizar_chat_agente"]
