import math
import streamlit as st
import MetaTrader5 as mt5  # type: ignore[import-untyped]
from tools.mt5_bridge import (
    inicializar_mt5, obtener_precio_actual, obtener_datos_historicos, resolver_simbolo,
)

# Puntos máximos del mini-gráfico (sparkline) por símbolo
_SPARK_MAX = 40


@st.cache_data(ttl=120, show_spinner=False)
def _historial_sparkline(simbolo: str) -> list:
    """Últimos ~30 cierres (M1) para sembrar el sparkline. Cacheado 2 min.
    Se llama en la carga inicial (hilo principal), no en el refresco en vivo."""
    try:
        df = obtener_datos_historicos(simbolo, timeframe=mt5.TIMEFRAME_M1, n_velas=30)
        if df is not None and not df.empty and "close" in df.columns:
            return [float(x) for x in df["close"].tolist()][-_SPARK_MAX:]
    except Exception:
        pass
    return []


def _empujar_spark(simbolo: str, precio: float):
    """Agrega un precio al buffer del sparkline (crece con el refresco en vivo)."""
    if not precio or precio <= 0:
        return
    buf = st.session_state.setdefault("_spark", {}).setdefault(simbolo, [])
    buf.append(float(precio))
    if len(buf) > _SPARK_MAX:
        del buf[:-_SPARK_MAX]
from tools import watchlist_manager as wl


def construir_entrada(simbolo: str) -> dict:
    """Arma la entrada de un símbolo para la watchlist (nombre, categoría, precio)
    usando el nombre EXACTO de MT5 (sin limpiar los '...')."""
    try:
        sim_real = resolver_simbolo(simbolo)  # nombre real en ESTE terminal (con/sin '...')
        mt5.symbol_select(sim_real, True)
        info = mt5.symbol_info(sim_real)
    except Exception:
        info = None
    nombre = (info.description if info and getattr(info, "description", "") else wl.nombre_visible(simbolo))
    mercado = wl.categoria_simbolo(getattr(info, "path", "") if info else "", simbolo)
    precio = 0.0
    try:
        tick = obtener_precio_actual(simbolo)
        if "error" not in tick:
            precio = tick.get("last", 0) if tick.get("last", 0) > 0 else tick.get("bid", 0)
    except Exception:
        pass
    return {
        "nombre": nombre,
        "mercado": mercado,
        "precio": float(precio or 0.0),
        "var": "+0.00 (0.00%)",
        "sube": True,
    }


def cargar_datos_mercado():
    # Inicializar conexión a MT5 de forma segura al cargar el mercado
    inicializar_mt5()

    # Si ya se cargó una vez, no repetir el fetch pesado; los fragmentos
    # (actualizar_precios_mt5) mantienen los precios en vivo.
    if st.session_state.get("datos_cargados"):
        return

    # 1. Índices globales (barra superior) — se mantiene con yfinance
    if "datos_indices_globales" not in st.session_state:
        st.session_state.datos_indices_globales = {
            "SP500": {"valor": 5432.18, "var": "+0.84%", "sube": True},
            "NASDAQ": {"valor": 17742.90, "var": "+1.22%", "sube": True},
            "DOW": {"valor": 39310.44, "var": "-0.31%", "sube": False},
            "BTC": {"valor": 67204.00, "var": "+2.90%", "sube": True},
        }
    try:
        import yfinance as yf  # type: ignore[import-untyped]
        simbolos_indices = {"SP500": "^GSPC", "NASDAQ": "^IXIC", "DOW": "^DJI", "BTC": "BTC-USD"}
        for key, sym in simbolos_indices.items():
            hist = yf.Ticker(sym).history(period="3d")
            if not hist.empty and "Close" in hist.columns:
                val = hist["Close"].iloc[-1]
                if not math.isnan(float(val)):
                    actual = float(val)
                    anterior_val = hist["Close"].iloc[-2] if len(hist) > 1 else actual
                    anterior = float(anterior_val) if not math.isnan(float(anterior_val)) else actual
                    cambio = actual - anterior
                    porc = (cambio / anterior * 100) if anterior != 0 else 0.0
                    st.session_state.datos_indices_globales[key] = {
                        "valor": actual, "var": f"{'+' if cambio >= 0 else ''}{porc:.2f}%", "sube": cambio >= 0}
    except Exception:
        pass

    # 2. Watchlist del USUARIO (desde Supabase; si es nuevo, se siembra el default)
    usuario = st.session_state.get("usuario_info", {})
    uid = usuario.get("id") if isinstance(usuario, dict) else None
    simbolos = wl.obtener_watchlist(uid)
    if not simbolos:
        simbolos = wl.sembrar_defaults(uid)
    st.session_state.watchlist_simbolos = simbolos

    # 3. Construir los datos de mercado de esos símbolos (nombre EXACTO para MT5)
    datos = {}
    spark = st.session_state.setdefault("_spark", {})
    for sym in simbolos:
        datos[sym] = construir_entrada(sym)
        # Sembrar el sparkline con histórico M1 (una vez, en el hilo principal)
        if sym not in spark:
            spark[sym] = _historial_sparkline(sym)
    st.session_state.datos_mercado_real = datos

    st.session_state.datos_cargados = True


def actualizar_precios_mt5():
    """Actualización LIGERA de precios de la watchlist desde MT5 (tick en vivo).
    Usa el nombre EXACTO del símbolo (con '...') — sin limpiarlo."""
    inicializar_mt5()
    datos = st.session_state.get("datos_mercado_real")
    if not datos:
        return
    for simbolo in list(datos.keys()):
        try:
            info_tick = obtener_precio_actual(simbolo)
            if "error" in info_tick:
                continue
            precio_actual = info_tick.get("last", 0) if info_tick.get("last", 0) > 0 else info_tick.get("bid", 0)
            if precio_actual and precio_actual > 0:
                precio_anterior = datos[simbolo].get("precio", precio_actual)
                cambio = precio_actual - precio_anterior
                porcentaje = (cambio / precio_anterior * 100) if precio_anterior else 0.0
                decimales = 2 if precio_actual > 100 else 5
                datos[simbolo]["precio"] = precio_actual
                datos[simbolo]["sube"] = cambio >= 0
                if cambio != 0:
                    datos[simbolo]["var"] = f"{cambio:+.{decimales}f} ({porcentaje:+.2f}%)"
                _empujar_spark(simbolo, precio_actual)
        except Exception:
            pass
