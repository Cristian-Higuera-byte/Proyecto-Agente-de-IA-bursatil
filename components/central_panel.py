"""Panel central del dashboard (compatibilidad).

Antes este archivo contenía todo (el gráfico, su HTML/JS y el chat del agente, casi 3000 líneas). Ahora cada
cosa vive en su sitio y aquí solo se re-exportan los nombres que usa app.py:

  renderizar_panel_central  ->  components/grafico/panel.py   (gráfico; su HTML/CSS/JS en grafico/estatico/)
  renderizar_chat_agente    ->  components/chat_agente.py
"""
from components.chat_agente import renderizar_chat_agente
from components.grafico.panel import renderizar_panel_central

__all__ = ["renderizar_chat_agente", "renderizar_panel_central"]
