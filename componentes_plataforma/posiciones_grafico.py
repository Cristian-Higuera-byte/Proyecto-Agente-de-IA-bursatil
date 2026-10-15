"""Trading desde el gráfico (posiciones, órdenes pendientes, TP/SL y clic derecho). El código vive en
componentes_plataforma/posiciones/ (datos iniciales, gatillos y el JavaScript por fragmentos en js/); este archivo se mantiene
para que el `from componentes_plataforma.posiciones_grafico import gatillos_cierre, js_posiciones` de grafico/panel.py
siga funcionando."""
from componentes_plataforma.posiciones import gatillos_cierre, js_posiciones

__all__ = ["js_posiciones", "gatillos_cierre"]
