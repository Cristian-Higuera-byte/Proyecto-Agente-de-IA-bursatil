"""Chat del agente de IA (core.agente.Agente): conversación, turno en segundo plano y botón de detener.

Va en la fila de abajo de app.py, junto al historial y las órdenes propuestas.

    sesion.py        id de usuario, creación/recuperación del agente, cambio de perfil, saludo inicial
    historial.py     sincroniza el turno en curso con la conversación y pinta los mensajes
    turno_vivo.py    burbuja de la respuesta que se está escribiendo (cronómetro + botón Detener)
    panel.py         renderizar_chat_agente(): tarjeta con controles, historial y caja de texto
"""
from components.chat.panel import renderizar_chat_agente

__all__ = ["renderizar_chat_agente"]
