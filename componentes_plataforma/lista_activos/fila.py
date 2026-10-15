"""Fila de un activo de la lista: tarjeta con ícono, precio y variación en vivo, y sus tres botones
(seleccionar, favorito y quitar)."""
import html
import re

import streamlit as st

from componentes_plataforma.iconos import icono_activo
from componentes_plataforma.lista_activos.acciones import agregar_favorito, quitar_de_lista, quitar_favorito
from componentes_plataforma.flujo_vivo import attrs as _live
from herramientas import gestor_lista_activos as wl


def dibujar_fila(ticker: str, item: dict) -> None:
    base = wl.nombre_visible(ticker)
    slug = re.sub(r"\W", "", ticker)
    is_selected = (st.session_state.activo_seleccionado == ticker)
    color_var = "#2ebd85" if item.get("sube", True) else "#f6465d"

    precio_val = item.get('precio', 1.0)
    formato_precio = f"${precio_val:,.2f}" if precio_val > 100 else f"{precio_val:,.5f}"

    nombre = html.escape(str(item.get('nombre', ticker)))
    variacion = html.escape(str(item.get('var', '+0.00%')))
    clase_sel = " sel" if is_selected else ""
    dir_cls = "up" if item.get("sube", True) else "down"

    es_favorito = ticker in st.session_state.get("favoritos", [])
    estrella = ":material/star:" if es_favorito else ":material/star_border:"
    ayuda = "Quitar de favoritos" if es_favorito else "Agregar a favoritos"

    with st.container(key=f"wlrow_{slug}"):
        # Tarjeta visual del activo
        st.markdown(f"""
            <div class='wl-row {dir_cls}{clase_sel}'>
                {icono_activo(ticker, 34)}
                <div class='wl-mid'>
                    <div class='wl-tk'>{html.escape(base)}</div>
                    <div class='wl-nm'>{nombre}</div>
                </div>
                <div class='wl-right'>
                    <div class='wl-px' {_live(ticker, 'px', pre='$' if precio_val > 100 else '')}>{formato_precio}</div>
                    <div class='wl-var' {_live(ticker, 'var', up='#2ebd85', dn='#f6465d')} style='color: {color_var};'>{variacion}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Botón invisible que cubre toda la fila -> selecciona el activo.
        # scope="app" fuerza una reejecución de TODA la app (no solo de
        # este fragmento), que es lo que hace que componentes_plataforma/central_panel.py
        # -- que lee este mismo st.session_state.activo_seleccionado --
        # cambie de inmediato el precio, el símbolo y el gráfico en vivo.
        if st.button("Seleccionar", key=f"wlsel_{slug}"):
            # OJO: no mostrar elementos (st.toast) aquí dentro del
            # fragmento justo antes de st.rerun(scope="app"): provoca
            # el error de frontend "Cannot set a node at a delta path"
            # y deja la app en blanco al cambiar de activo.
            st.session_state.activo_seleccionado = ticker
            st.rerun(scope="app")

        # Estrella de favoritos
        if st.button(
            estrella,
            key=f"wlfav_{slug}",
            help=ayuda,
            type="primary" if es_favorito else "secondary",
        ):
            if es_favorito:
                quitar_favorito(ticker)
            else:
                agregar_favorito(ticker)
            st.rerun(scope="app")

        # Quitar de mi lista (✕)
        if st.button(":material/close:", key=f"wlrm_{slug}", help="Quitar de mi lista"):
            quitar_de_lista(ticker)
            st.rerun(scope="app")
