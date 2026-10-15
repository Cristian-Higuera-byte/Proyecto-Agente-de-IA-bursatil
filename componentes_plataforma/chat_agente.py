"""Chat del agente de IA. El código vive en componentes_plataforma/chat/ (sesión, historial, turno en vivo y panel); este archivo
se mantiene para que `from componentes_plataforma.chat_agente import renderizar_chat_agente` (central_panel.py, aplicacion.py) siga
funcionando."""
from componentes_plataforma.chat import renderizar_chat_agente

__all__ = ["renderizar_chat_agente"]
