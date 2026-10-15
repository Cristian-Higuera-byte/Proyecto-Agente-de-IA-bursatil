"""Referencias de precio de un símbolo: cierre diario anterior y variación del día."""
import streamlit as st
import MetaTrader5 as mt5  # type: ignore[import-untyped]

from herramientas.puente_mt5 import obtener_datos_historicos


class SinDatos(Exception):
    """Se lanza dentro de las funciones cacheadas cuando MT5 aún no entrega
    histórico: st.cache_data NO cachea excepciones, así se reintenta luego."""


@st.cache_data(ttl=300, show_spinner=False)
def _cierre_previo_cache(simbolo: str) -> float:
    df = obtener_datos_historicos(simbolo, timeframe=mt5.TIMEFRAME_D1, n_velas=2)
    if df is None or len(df) < 2:
        raise SinDatos(simbolo)
    return float(df["close"].iloc[-2])


def cierre_previo(simbolo: str):
    """Cierre de la vela diaria anterior (base de la variación del día, igual
    que el feed en vivo de servidor_datos.py). Cacheado 5 min (solo si hay dato)."""
    try:
        return _cierre_previo_cache(simbolo)
    except Exception:
        return None


def variacion(simbolo: str, precio: float, decimales: int):
    """(texto, sube) de la variación del día, o None si no hay referencia."""
    previo = cierre_previo(simbolo)
    if not previo or not precio:
        return None
    cambio = precio - previo
    return f"{cambio:+.{decimales}f} ({cambio / previo * 100:+.2f}%)", cambio >= 0
