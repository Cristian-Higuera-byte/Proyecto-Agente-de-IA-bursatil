"""Vista de operar (Trading y Cartera), en dos filas."""
import streamlit as st

from componentes_plataforma.central_panel import renderizar_chat_agente, renderizar_panel_central
from componentes_plataforma.panel_ordenes import (inyectar_estilos_agente, renderizar_historial_agente,
                                      renderizar_ordenes_propuestas)

# Proporción de columnas compartida por las dos filas de la vista de operar, para que el
# historial quede bajo la lista, el chat bajo el gráfico y las propuestas bajo el ticket.
COLUMNAS_OPERAR = [1.7, 3.2, 0.95]
# Alto de las zonas con scroll del historial y de las propuestas, calculado para que su borde inferior
# coincida con el del chat (cabecera + selector + 450 de mensajes + campo de texto). Ajusta si no cuadra.
ALTURA_HISTORIAL = 587
ALTURA_PROPUESTAS = 500


def renderizar_vista_operativa(renderizar_lista_izquierda, fragmentos, consola) -> None:
    """Vista de operar (Trading y Cartera), en dos filas.

    Fila 1: lista (watchlist o posiciones) | gráfico | ticket de orden.
    Fila 2: historial del agente | chat del agente | órdenes propuestas.

    Los paneles del agente van en su propia fila, así quedan siempre a la altura del chat y
    no se desplazan cuando cambia el alto de la lista o del ticket de arriba."""
    fragmentos.favoritos()
    inyectar_estilos_agente()

    # El ticket ya no va como columna: vive en el rail de iconos fijo a la derecha
    # (componentes_plataforma/panel_riel.py). CSS del rail ANTES de las columnas para que el
    # gráfico se mida con el espacio reservado a la derecha.
    from componentes_plataforma.panel_riel import inyectar_css_rail, renderizar_rail_y_paneles
    inyectar_css_rail()

    col_izquierda, col_center = st.columns([COLUMNAS_OPERAR[0],
                                            COLUMNAS_OPERAR[1] + COLUMNAS_OPERAR[2]])
    with col_izquierda:
        renderizar_lista_izquierda()
    with col_center:
        renderizar_panel_central(consola)
    renderizar_rail_y_paneles(consola)

    st.markdown("---")

    col_historial, col_chat, col_propuestas = st.columns(COLUMNAS_OPERAR)
    with col_historial:
        renderizar_historial_agente(altura=ALTURA_HISTORIAL)
    with col_chat:
        renderizar_chat_agente()
    with col_propuestas:
        renderizar_ordenes_propuestas(altura=ALTURA_PROPUESTAS)
