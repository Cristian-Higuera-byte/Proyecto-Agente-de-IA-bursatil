"""
componentes_plataforma/operacion_un_clic
----------------------------
Modo "One-Click Trading" (como MT5): con el interruptor activo, las órdenes del
ticket, del menú del clic derecho del gráfico y los arrastres de líneas
(Buy/Sell Limit/Stop, Take Profit, Stop Loss) se envían SIN confirmación.

La PRIMERA vez que un usuario lo activa debe aceptar la renuncia de
responsabilidades (modal). La aceptación queda registrada en el servidor, con
fecha, en `data/one_click_aceptaciones.json` (ignorado por git) y no se vuelve a
pedir. El interruptor vive en el ticket de órdenes (clave `ord_oc`); el gráfico
lee su estado del DOM y, para activarlo desde el menú, pulsa ese mismo interruptor.

Uso:
- order_panel.py: `st.toggle(..., key="ord_oc", on_change=al_cambiar)`
- aplicacion.py: `render_modal_terminos()` (fuera de los fragmentos en vivo)

Archivos: registro.py (aceptación por usuario; PEDIR_SIEMPRE vive aquí), estado.py (callbacks del
interruptor), dialogo.py (ventana), terminos.html (texto legal) y estilos.css.
"""
from componentes_plataforma.operacion_un_clic.dialogo import render_modal_terminos
from componentes_plataforma.operacion_un_clic.estado import al_cambiar, pedir_terminos_si_corresponde
from componentes_plataforma.operacion_un_clic.registro import PEDIR_SIEMPRE, aceptado

__all__ = ["aceptado", "al_cambiar", "pedir_terminos_si_corresponde", "render_modal_terminos", "PEDIR_SIEMPRE"]
