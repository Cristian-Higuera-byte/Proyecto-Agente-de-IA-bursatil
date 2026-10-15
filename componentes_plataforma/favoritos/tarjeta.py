"""Tarjeta «burbuja» de un favorito: contorno degradé verde (sube) / rojo (baja), ícono, nombre, precio en
vivo, variación y flecha de tendencia."""
from __future__ import annotations

import streamlit as st

from componentes_plataforma.iconos import icono_activo as _icono
from componentes_plataforma.flujo_vivo import attrs as _live


def icono_activo(ticker: str, size: int = 30) -> str:
    """Ícono del activo (estilo XM). Lo define componentes_plataforma/iconos.py para todo el
    dashboard; se mantiene aquí por compatibilidad con quien lo importa."""
    return _icono(ticker, size)


def fmt_precio(precio: float) -> str:
    if precio >= 100:
        return f"{precio:,.2f}"
    return f"{precio:,.5f}"


def tarjeta_html(tk: str, datos: dict) -> str:
    item = datos.get(tk, {"precio": 0.0, "var": "", "sube": True})
    sube = item.get("sube", True)
    dir_cls = "up" if sube else "down"
    color = "#3fb950" if sube else "#f85149"
    flecha = "↗" if sube else "↘"
    precio = item.get("precio", 0.0)
    var = item.get("var", "") or "0.00 (0.00%)"
    nombre = tk.replace("...", "")
    sel = " sel" if st.session_state.get("activo_seleccionado") == tk else ""
    return (
        f"<div class='fav-card {dir_cls}{sel}'>"
        f"<span class='fav-ic'>{icono_activo(tk)}</span>"
        "<div class='fav-l'>"
        f"<div class='fav-tk'>{nombre}</div>"
        "<div class='fav-row'>"
        f"<span class='fav-px' {_live(tk, 'px')}>{fmt_precio(precio)}</span>"
        f"<span class='fav-var' {_live(tk, 'var')} style='color:{color};'>{var}</span>"
        "</div></div>"
        f"<span class='fav-arrow' style='color:{color};'>{flecha}</span>"
        "</div>"
    )
