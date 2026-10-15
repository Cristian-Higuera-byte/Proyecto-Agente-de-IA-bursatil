"""
Paquete del ticket de órdenes (Order Entry). La API pública es `renderizar_panel_orden`,
que importa componentes_plataforma/panel_riel.py; el resto son submódulos internos del paquete:
  panel · cuenta · ejecucion · confirmacion · calculadora · avisos · interfaz (+ estatico/).
"""
from .panel import renderizar_panel_orden

__all__ = ["renderizar_panel_orden"]
