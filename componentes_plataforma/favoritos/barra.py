"""Barra de favoritos: panel con encabezado «Mis favoritos» + contador y 6 slots (favorito con ✕, «+» en el
primer hueco libre, o vacío)."""
from __future__ import annotations

import re
from pathlib import Path

import streamlit as st

from componentes_plataforma import _estaticos
from componentes_plataforma.favoritos.estado import FAVORITOS_MAX, agregar_favorito, inicializar_favoritos, quitar_favorito
from componentes_plataforma.favoritos.tarjeta import tarjeta_html

_VISIBLES = 6           # tarjetas visibles
_CSS = Path(__file__).parent / "estilos.css"


def _slot_agregar(disponibles):
    """Tarjeta '+' en el hueco libre: popover con selector para agregar favorito."""
    with st.container(key="favadd"):
        with st.popover("＋", help="Agregar favorito", use_container_width=True):
            sel = st.selectbox(
                "Agregar activo", options=[""] + disponibles,
                format_func=lambda x: "Elegir activo…" if x == "" else x.replace("...", ""),
                label_visibility="collapsed", key="fav_add_sel",
            )
            if sel:
                agregar_favorito(sel)
                st.rerun(scope="fragment")


def _slot_favorito(tk: str, datos: dict):
    st.html(tarjeta_html(tk, datos))
    # Clic en la tarjeta -> carga el activo en el gráfico, el ticket y la cabecera (igual que la watchlist).
    # scope="app" porque esos paneles están fuera de este fragmento. Sin st.toast antes del rerun
    # (error "Cannot set a node at a delta path", ver watchlist.py).
    slug = re.sub(r"\W", "", tk)
    if st.button("Seleccionar", key=f"favsel_{slug}"):
        st.session_state.activo_seleccionado = tk
        st.rerun(scope="app")
    if st.button("✕", key=f"favx_{tk}", help="Quitar de favoritos"):
        quitar_favorito(tk)
        st.rerun(scope="fragment")


def renderizar_barra_favoritos():
    inicializar_favoritos()
    datos = st.session_state.get("datos_mercado_real", {})
    favs = list(st.session_state.favoritos)
    lista = st.session_state.get("watchlist_simbolos") or list(datos.keys())
    disponibles = [t for t in lista if t not in favs]
    total = len(favs)
    puede_agregar = bool(disponibles) and total < FAVORITOS_MAX

    with st.container(key="fav_panel"):
        st.html(_estaticos.estilos(_CSS))

        # --- Encabezado: solo título + contador ---
        st.html(
            "<div class='fav-head'>"
            "<span class='fav-chip'><span class='fav-mi'>star</span></span>"
            "<span class='fav-title'>Mis favoritos</span>"
            f"<span class='fav-badge'>{total}</span></div>"
        )

        # --- 6 slots: favorito (con ✕), '+' en el primer hueco libre, o vacío ---
        cols = st.columns(_VISIBLES, gap="small")
        for i in range(_VISIBLES):
            with cols[i]:
                with st.container(key=f"favslot_{i}"):
                    if i < total:
                        _slot_favorito(favs[i], datos)
                    elif i == total and puede_agregar:
                        _slot_agregar(disponibles)
                    else:
                        st.html("<div class='fav-card' style='visibility:hidden;'></div>")
