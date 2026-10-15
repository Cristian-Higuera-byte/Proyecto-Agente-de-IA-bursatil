"""Barra de precio en vivo que va encima del gráfico (símbolo, precio, Bid/Ask y estado de la conexión)."""
from __future__ import annotations

from html import escape

import streamlit as st

from componentes_plataforma.flujo_vivo import attrs as _live, intervalo as _intervalo
from herramientas.puente_mt5 import obtener_precio_actual


def renderizar_cabecera_precio(activo_visible: str, digits: int) -> None:
    @st.fragment(run_every=_intervalo("2s"))   # con feed: lo pinta flujo_vivo.py
    def _cabecera_precio():
        info_tick = obtener_precio_actual(activo_visible)
        conectado = "error" not in info_tick
        if conectado:
            precio_actual = info_tick.get("last", 0) if info_tick.get("last", 0) > 0 else info_tick.get("bid", 0)
        else:
            precio_actual = 0.0
        bid = float(info_tick.get("bid", 0) or 0)
        ask = float(info_tick.get("ask", 0) or 0)
        conectado = conectado and precio_actual > 0

        clave = f"_prev_precio_{activo_visible}"
        clave_color = f"_color_precio_{activo_visible}"
        if conectado:
            anterior = st.session_state.get(clave, precio_actual)
            if precio_actual > anterior:
                color_var_activo = "#3fb950"
            elif precio_actual < anterior:
                color_var_activo = "#f85149"
            else:
                color_var_activo = st.session_state.get(clave_color, "#3fb950")
            st.session_state[clave] = precio_actual
            st.session_state[clave_color] = color_var_activo
        else:
            color_var_activo = "#8b949e"

        color_estado = "#3fb950" if conectado else "#f85149"
        texto_estado = "Conectado" if conectado else "Sin conexión"
        
        st.markdown(f"""
            <div style='background-color: #161b22; padding: 10px 16px; border-radius: 8px; border: 1px solid #30363d; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;'>
                <div style='display: flex; align-items: center; gap: 14px;'>
                    <span style='font-size: 20px; font-weight: bold; color: #ffffff;'>{escape(activo_visible)}</span>
                    <span style='background: #30363d; color: #8b949e; padding: 2px 8px; border-radius: 4px; font-size: 11px;'>XM / MT5</span>
                    <span {_live(activo_visible, 'px', d=digits, flash=1)} style='font-size: 22px; font-weight: bold; font-family: monospace; color: {color_var_activo};'>{precio_actual:,.{digits}f}</span>
                    <span style='font-size: 14px; font-weight: 600; color: {color_var_activo};'>Bid: <span {_live(activo_visible, 'bid', d=digits)}>{bid:,.{digits}f}</span> | Ask: <span {_live(activo_visible, 'ask', d=digits)}>{ask:,.{digits}f}</span></span>
                </div>
                <div style='font-size: 13px; color: #8b949e; font-weight: 600; display: flex; align-items: center; gap: 6px;'>
                    {texto_estado} <span style='color: {color_estado}; font-size: 16px;'>●</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    _cabecera_precio()
