"""Datos del bróker (MT5): símbolos disponibles, resolución de nombres, estado del mercado y filas de la tabla."""
import re

import streamlit as st
from proveedores.selector_mt5 import mt5  # type: ignore[import-untyped]

from componentes_plataforma.mercado_datos import cierre_previo as _cierre_previo
from componentes_plataforma.mercados.constantes import CATALOGO
from herramientas.puente_mt5 import MT5_LOCK, obtener_datos_historicos, resolver_simbolo


def g(info, attr):
    return getattr(info, attr, 0) or 0


class SinDatos(Exception):
    """MT5 no entregó datos: se lanza para que st.cache_data NO cachee el vacío."""


@st.cache_data(ttl=600, show_spinner=False)
def _indice_broker_cache():
    with MT5_LOCK:
        simbolos = mt5.symbols_get() or []
    if not simbolos:
        raise SinDatos("symbols_get")
    nombres = {s.name for s in simbolos}
    por_ticker = {}
    for s in simbolos:
        # "Apple Inc (AAPL.OQ)" -> AAPL ; se ignoran las variantes _turbo
        m = re.search(r"\(([A-Za-z0-9\-]+)(?:\.[A-Za-z]+)?\)\s*$", s.description or "")
        if m and "_turbo" not in s.name:
            por_ticker.setdefault(m.group(1).upper(), s.name)
    return nombres, por_ticker


def _indice_broker():
    try:
        return _indice_broker_cache()
    except Exception:
        return set(), {}


def resolver(candidatos) -> str | None:
    """Nombre real en el bróker del primer candidato que exista, o None."""
    nombres, por_ticker = _indice_broker()
    if not nombres:
        return None
    for c in candidatos:
        r = resolver_simbolo(c)
        if r in nombres:
            return r
        if c + "Cash" in nombres:                         # XM: FRA40Cash, SpainCash...
            return c + "Cash"
        futuros = sorted(n for n in nombres if n.upper().startswith(c.upper() + "-"))
        if futuros:                                       # XM: COCOA-DEC26
            return futuros[0]
    for c in candidatos:                                  # acciones: ticker en la descripción
        if c.upper() in por_ticker:
            return por_ticker[c.upper()]
    return None


@st.cache_data(ttl=600, show_spinner=False)
def _items_cache(categoria: str):
    out = []
    for i, (cands, nombre) in enumerate(CATALOGO.get(categoria, [])):
        real = resolver(cands)
        if real:
            out.append((real, nombre, i))
    if not out:
        raise SinDatos(categoria)        # MT5 sin conexión: no cachear el vacío
    return out


def items(categoria: str):
    """[(real, nombre, índice)] de la categoría, solo los que existen en el bróker."""
    try:
        return _items_cache(categoria)
    except Exception:
        return []


@st.cache_data(ttl=10, show_spinner=False)
def hora_servidor() -> int:
    """Hora del servidor del bróker (unix) ≈ último tick de las cripto (cotizan 24/7)."""
    mejor = 0
    for c in ("BTCUSD", "ETHUSD", "EURUSD"):
        try:
            with MT5_LOCK:
                t = mt5.symbol_info_tick(resolver_simbolo(c))
            mejor = max(mejor, int(getattr(t, "time", 0) or 0))
        except Exception:
            pass
    return mejor


def esta_abierto(t_tick: int) -> bool:
    ref = hora_servidor()
    return bool(t_tick and ref and ref - t_tick < 180)


@st.cache_data(ttl=300, show_spinner=False)
def _serie_cache(real: str, tf: int, n: int):
    df = obtener_datos_historicos(real, timeframe=tf, n_velas=n)
    if df is None or df.empty:
        raise SinDatos(real)
    return df


def serie(real: str, tf: int, n: int):
    try:
        return _serie_cache(real, tf, n)
    except Exception:
        return None


def fila(real: str, nombre: str):
    """Datos de una fila desde MT5, o None si no hay precio."""
    try:
        with MT5_LOCK:
            mt5.symbol_select(real, True)
            info = mt5.symbol_info(real)
            tick = mt5.symbol_info_tick(real) if info is not None else None
    except Exception:
        return None
    if info is None:
        return None
    last = float(getattr(tick, "bid", 0) or 0) if tick is not None else 0.0
    if last <= 0:
        last = float(g(info, "bid") or g(info, "last"))
    if last <= 0:   # bolsa cerrada (acciones antes de la apertura): último cierre diario
        d1 = serie(real, mt5.TIMEFRAME_D1, 2)
        last = float(d1["close"].iloc[-1]) if d1 is not None else 0.0
    if last <= 0:
        return None
    dig = int(g(info, "digits") or 2)
    hi = float(g(info, "bidhigh") or last)
    lo = float(g(info, "bidlow") or last)
    prev = _cierre_previo(real)
    ch = (last - prev) if prev else 0.0
    pct = (ch / prev * 100) if prev else 0.0
    return {"sym": real, "label": nombre, "last": last, "hi": max(hi, last), "lo": min(lo, last),
            "ch": ch, "pct": pct, "dig": dig, "t": int(getattr(tick, "time", 0) or 0),
            "desc": getattr(info, "description", "") or ""}
