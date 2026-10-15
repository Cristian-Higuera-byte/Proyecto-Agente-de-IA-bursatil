"""Acciones de la lista de activos: favoritos (con respaldo si no existe el módulo) y quitar un símbolo."""
from typing import Any

import streamlit as st

try:
    from componentes_plataforma.favoritos_barra import agregar_favorito, quitar_favorito
except ImportError:
    def agregar_favorito(ticker: str) -> Any:
        _ = ticker
        return None

    def quitar_favorito(ticker: str) -> Any:
        _ = ticker
        return None


def quitar_de_lista(ticker: str):
    """Quita un símbolo de la watchlist del usuario (Supabase + sesión)."""
    from herramientas import gestor_lista_activos as wl
    uid = (st.session_state.get("usuario_info") or {}).get("id")
    wl.quitar_simbolo(uid, ticker)
    st.session_state.get("datos_mercado_real", {}).pop(ticker, None)
    lst = st.session_state.get("watchlist_simbolos", [])
    if ticker in lst:
        lst.remove(ticker)
    favs = st.session_state.get("favoritos", [])
    if ticker in favs:
        favs.remove(ticker)
    if st.session_state.get("activo_seleccionado") == ticker:
        restantes = list(st.session_state.get("datos_mercado_real", {}).keys())
        st.session_state.activo_seleccionado = restantes[0] if restantes else "EURUSD..."
