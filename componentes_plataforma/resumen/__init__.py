"""
componentes_plataforma/resumen
------------------
Vista "Resumen": dashboard del portafolio (sección F). Tarjetas KPI con icono,
acento de color y micro-interacción (hover), nivel de margen como barra, curva de
balance con selector de periodo (interactivo) y exposición por activo. Todos los
números salen de herramientas.estadisticas_portafolio (datos reales de MT5). Estética P&J:
fondo oscuro, números grandes, verde/rojo según signo, acento naranja del logo.

Limitaciones honestas que la propia UI indica:
  - Drawdown mostrado = de BALANCE (MT5 no guarda snapshots de equity).
  - Dividendos: si el bróker/demo no generó eventos, muestra "sin dividendos".

Archivos: panel.py, secciones.py (bloques), tarjetas.py, curva.py, formato.py, datos.py + datos.json y estilos.css.
"""
from componentes_plataforma.resumen.panel import renderizar_panel_resumen

__all__ = ["renderizar_panel_resumen"]
