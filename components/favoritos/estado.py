"""Favoritos del usuario: viven en `st.session_state.favoritos` y se guardan por usuario en Supabase
(columna `favorito` de watchlist_usuario, vía tools/watchlist_manager)."""
from __future__ import annotations

import streamlit as st

from tools import watchlist_manager as wl

FAVORITOS_MAX = 6       # tope de favoritos por usuario (solo caben 6 en una fila)
FAVORITOS_DEFAULT = wl.FAVORITOS_DEFAULT


def _uid():
    usuario = st.session_state.get("usuario_info") or {}
    return usuario.get("id") if isinstance(usuario, dict) else None


def inicializar_favoritos():
    """Carga los favoritos del usuario desde Supabase (una vez por sesión)."""
    if "favoritos" not in st.session_state:
        favs = wl.obtener_favoritos(_uid())
        st.session_state.favoritos = favs if favs else list(FAVORITOS_DEFAULT)


def agregar_favorito(ticker: str):
    """Agrega un activo a favoritos (respetando el máximo y sin duplicar)."""
    inicializar_favoritos()
    limpio = ticker.replace("...", "")
    if ticker in st.session_state.favoritos:
        st.toast(f"⭐ {limpio} ya está en tus favoritos")
        return
    if len(st.session_state.favoritos) >= FAVORITOS_MAX:
        st.toast(f"⚠️ Máximo {FAVORITOS_MAX} favoritos. Quita uno primero.")
        return
    st.session_state.favoritos.append(ticker)
    wl.marcar_favorito(_uid(), ticker, True)
    st.toast(f"⭐ {limpio} agregado a favoritos")


def quitar_favorito(ticker: str):
    inicializar_favoritos()
    if ticker in st.session_state.favoritos:
        st.session_state.favoritos.remove(ticker)
        wl.marcar_favorito(_uid(), ticker, False)
