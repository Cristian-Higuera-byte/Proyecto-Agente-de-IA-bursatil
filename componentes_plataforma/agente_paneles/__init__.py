"""Paneles del agente en los costados del dashboard (Fase 1).

NOMBRE DEL PAQUETE: componentes_plataforma/agente_paneles

  * renderizar_historial_agente()   -> panel IZQUIERDO (bajo la watchlist): historial
    permanente de cada orden que el agente propuso, ejecutada, rechazada o bloqueada.
  * renderizar_ordenes_propuestas() -> panel DERECHO (sobre el ticket): propuestas
    pendientes con Confirmar / Rechazar, interruptor de emergencia y avisos.

Se llaman desde aplicacion.py (vistas Trading y Cartera), así que se dibujan en CADA ejecución de la
app, hagas o no una petición al agente (ya no dependen del chat). aplicacion.py llama una sola vez a
inyectar_estilos_agente() para cargar el CSS de ambos paneles.

Vigilancia automática (nucleo_agente/vigilancia.py): el panel derecho muestra además las vigilancias pendientes de
autorizar (con su botón Autorizar) y las activas (con su estado y un botón Detener). Lo que el motor
ejecuta solo queda en el historial marcado como AUTO.

No usan run_every: un temporizador reinicia la ejecución en curso y cortaría la respuesta
del agente mientras escribe. En su lugar, central_panel.py hace un st.rerun() al terminar un
turno en el que el agente propuso algo, y Confirmar / Rechazar refrescan toda la app.

Solo este módulo (vía nucleo_agente.ordenes.confirmar_orden) puede hacer que una orden llegue a MT5.

Archivos: historial.py, propuestas.py, vigilancias.py, formato.py, datos.py + estados.json y estilos.css.
"""
import streamlit as st

from componentes_plataforma.agente_paneles.estilos import CSS
from componentes_plataforma.agente_paneles.formato import cabecera_agente
from componentes_plataforma.agente_paneles.historial import renderizar_historial_agente
from componentes_plataforma.agente_paneles.propuestas import renderizar_ordenes_propuestas


def inyectar_estilos_agente() -> None:
    """Carga el CSS de los dos paneles del agente. Llamar UNA vez por ejecución (lo hace aplicacion.py)."""
    st.html(CSS)


__all__ = ["inyectar_estilos_agente", "renderizar_historial_agente", "renderizar_ordenes_propuestas", "cabecera_agente"]
