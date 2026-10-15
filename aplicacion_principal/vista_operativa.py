# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# -------------------------------- INICIO Piña y Jara vista_operativa .PY -------------------------------
# -------------------------------------------------------------------------------------------------------

"""
Vista de operar, compartida por las secciones Trading y Cartera.

Se dibuja en dos filas: arriba la lista de activos o posiciones, el gráfico y (a la derecha, en un
rail de iconos fijo) el ticket de orden; abajo el historial del agente, el chat y las órdenes
propuestas.
"""
import streamlit as st

from componentes_plataforma.central_panel import renderizar_chat_agente, renderizar_panel_central
from componentes_plataforma.panel_ordenes import (inyectar_estilos_agente, renderizar_historial_agente,
                                      renderizar_ordenes_propuestas)

# Proporción de columnas compartida por las dos filas de la vista de operar, para que el
# historial quede bajo la lista, el chat bajo el gráfico y las propuestas bajo el ticket.
COLUMNAS_OPERAR = [1.7, 3.2, 0.95]
# Alto de las zonas con scroll del historial y de las propuestas, calculado para que su borde
# inferior coincida con el del chat (cabecera + selector + 450 de mensajes + campo de texto).
# Se ajusta si no cuadra.
ALTURA_HISTORIAL = 587
ALTURA_PROPUESTAS = 500


def renderizar_vista_operativa(renderizar_lista_izquierda, fragmentos, consola) -> None:
    """
    Dibuja la vista de operar (Trading y Cartera) en dos filas.

    Fila 1: lista de la izquierda (watchlist o posiciones) | gráfico | ticket de orden.
    Fila 2: historial del agente | chat del agente | órdenes propuestas.

    Los paneles del agente van en su propia fila para que queden siempre a la altura del chat y no
    se desplacen cuando cambia el alto de la lista o del ticket de arriba.

    Recibe `renderizar_lista_izquierda` (la función que dibuja la lista de la izquierda, distinta
    en Trading y en Cartera), `fragmentos` (el objeto de `crear_fragmentos()`) y `consola` (el
    módulo `consola_agente`, o `None`), que se pasa a los paneles que lo usan.
    """
    fragmentos.favoritos()
    inyectar_estilos_agente()

    # El ticket ya no va como columna: vive en el rail de iconos fijo a la derecha
    # (componentes_plataforma/panel_riel.py). El CSS del rail se inyecta ANTES de las columnas
    # para que el gráfico se mida con el espacio reservado a la derecha.
    from componentes_plataforma.panel_riel import inyectar_css_riel, renderizar_riel_y_paneles
    inyectar_css_riel()

    # Primera fila: lista a la izquierda y panel central (gráfico) a la derecha.
    col_izquierda, col_centro = st.columns([COLUMNAS_OPERAR[0],
                                            COLUMNAS_OPERAR[1] + COLUMNAS_OPERAR[2]])
    with col_izquierda:
        renderizar_lista_izquierda()
    with col_centro:
        renderizar_panel_central(consola)
    renderizar_riel_y_paneles(consola)

    st.markdown("---")

    # Segunda fila: paneles del agente, con las mismas proporciones que la primera.
    col_historial, col_chat, col_propuestas = st.columns(COLUMNAS_OPERAR)
    with col_historial:
        renderizar_historial_agente(altura=ALTURA_HISTORIAL)
    with col_chat:
        renderizar_chat_agente()
    with col_propuestas:
        renderizar_ordenes_propuestas(altura=ALTURA_PROPUESTAS)


# -------------------------------------------------------------------------------------------------------
# --------------------------------- FIN Piña y Jara vista_operativa .PY ---------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
