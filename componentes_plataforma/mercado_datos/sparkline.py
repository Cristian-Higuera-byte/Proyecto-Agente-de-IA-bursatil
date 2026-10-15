"""Mini-gráfico (sparkline) de cada símbolo: semilla con histórico M1 y buffer que crece con cada tick."""
import streamlit as st
import MetaTrader5 as mt5  # type: ignore[import-untyped]

from componentes_plataforma.mercado_datos.referencias import SinDatos
from herramientas.puente_mt5 import obtener_datos_historicos

# Puntos máximos del mini-gráfico (sparkline) por símbolo
SPARK_MAX = 40


@st.cache_data(ttl=120, show_spinner=False)
def _historial_sparkline_cache(simbolo: str) -> list:
    df = obtener_datos_historicos(simbolo, timeframe=mt5.TIMEFRAME_M1, n_velas=30)
    if df is None or df.empty or "close" not in df.columns:
        raise SinDatos(simbolo)
    return [float(x) for x in df["close"].tolist()][-SPARK_MAX:]


def historial_sparkline(simbolo: str) -> list:
    """Últimos ~30 cierres (M1) para sembrar el sparkline. Cacheado 2 min.
    Hallazgo: en un símbolo recién agregado (p. ej. GOLD o Adidas en XM) la
    primera lectura viene VACÍA porque el terminal todavía está descargando su
    historial; antes ese [] se cacheaba y el mini-gráfico quedaba plano."""
    try:
        return _historial_sparkline_cache(simbolo)
    except Exception:
        return []


def asegurar_semilla(simbolo: str):
    """Si el sparkline de un símbolo está vacío o casi (recién agregado, o la
    primera lectura vino vacía), lo vuelve a sembrar con el histórico M1."""
    spark = st.session_state.setdefault("_spark", {})
    buf = spark.get(simbolo) or []
    if len(buf) >= 5:
        return
    hist = historial_sparkline(simbolo)
    if hist:
        spark[simbolo] = (hist + buf)[-SPARK_MAX:]


def empujar_spark(simbolo: str, precio: float):
    """Agrega un precio al buffer del sparkline (crece con el refresco en vivo)."""
    if not precio or precio <= 0:
        return
    buf = st.session_state.setdefault("_spark", {}).setdefault(simbolo, [])
    buf.append(float(precio))
    if len(buf) > SPARK_MAX:
        del buf[:-SPARK_MAX]
