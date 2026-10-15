"""
componentes_plataforma/diario
------------------
Vista "Diario" (Trading Journal, sección E): registro automático de operaciones
cerradas desde MT5 + métricas (win rate, profit factor, R/R, expectancy, drawdown)
+ ficha por operación con mini-gráfico auto-generado y notas editables (estrategia,
emoción, razón) y R/R planificado/realizado.

Archivos: panel.py (arma la vista), tabla.py, ficha.py, mini_grafico.py, formato.py,
datos.json (estrategias y emociones) y estilos.css.

Estética alineada con el historial de la vista Inicio (tabla `pos`, íconos de
activo, pills BUY/SELL, verde/rojo con la paleta P&J). Datos de estadisticas_diario /
almacen_diario.
"""
from componentes_plataforma.diario.panel import renderizar_panel_journal

__all__ = ["renderizar_panel_journal"]
