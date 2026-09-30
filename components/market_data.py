import math
import streamlit as st
import MetaTrader5 as mt5  # type: ignore[import-untyped]
from tools.mt5_bridge import inicializar_mt5, obtener_precio_actual
from tools import watchlist_manager as wl


def obtener_simbolo_mt5_real(simbolo: str) -> str:
    """Busca y valida el nombre real del símbolo en MT5 usando coincidencias generales,
    resolviendo problemas con sufijos o puntos suspensivos (...)."""
    if not mt5.initialize():
        return simbolo
    
    # 1. Intentar primero con el nombre exacto por si acaso
    if mt5.symbol_info(simbolo) is not None:
        return simbolo
    
    # 2. Si falla, limpiar el símbolo (quitar '...' y sufijos) usando watchlist_manager
    base = wl.nombre_visible(simbolo)
    
    # 3. Búsqueda por coincidencia general en MT5 (ej. *EURUSD*)
    coincidencias = mt5.symbols_get(f"*{base}*")
    if coincidencias:
        return coincidencias[0].name
        
    return simbolo


def construir_entrada(simbolo: str) -> dict:
    """Arma la entrada de un símbolo para la watchlist resolviendo el nombre real en MT5."""
    simbolo_real = obtener_simbolo_mt5_real(simbolo)
    
    try:
        mt5.symbol_select(simbolo_real, True)
        info = mt5.symbol_info(simbolo_real)
    except Exception:
        info = None
        
    nombre = (info.description if info and getattr(info, "description", "") else wl.nombre_visible(simbolo))
    mercado = wl.categoria_simbolo(getattr(info, "path", "") if info else "", simbolo_real)
    precio = 0.0
    
    try:
        tick = obtener_precio_actual(simbolo_real)
        if "error" not in tick:
            precio = tick.get("last", 0) if tick.get("last", 0) > 0 else tick.get("bid", 0)
    except Exception:
        pass
        
    return {
        "simbolo_real": simbolo_real,
        "nombre": nombre,
        "mercado": mercado,
        "precio": float(precio or 0.0),
        "var": "+0.00 (0.00%)",
        "sube": True,
    }


def cargar_datos_mercado():
    # Inicializar conexión a MT5 de forma segura al cargar el mercado
    inicializar_mt5()

    if st.session_state.get("datos_cargados"):
        return

    # 1. Índices globales (barra superior)
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

    # 2. Watchlist del USUARIO
    usuario = st.session_state.get("usuario_info", {})
    uid = usuario.get("id") if isinstance(usuario, dict) else None
    simbolos = wl.obtener_watchlist(uid)
    if not simbolos:
        simbolos = wl.sembrar_defaults(uid)
    st.session_state.watchlist_simbolos = simbolos

    # 3. Construir los datos de mercado usando la resolución de nombres generales
    datos = {}
    for sym in simbolos:
        datos[sym] = construir_entrada(sym)
    st.session_state.datos_mercado_real = datos

    st.session_state.datos_cargados = True


def actualizar_precios_mt5():
    """Actualización LIGERA de precios de la watchlist usando coincidencias generales de MT5."""
    inicializar_mt5()
    datos = st.session_state.get("datos_mercado_real")
    if not datos:
        return
    for simbolo in list(datos.keys()):
        try:
            # Resolver el símbolo real en cada iteración por seguridad
            simbolo_real = datos[simbolo].get("simbolo_real") or obtener_simbolo_mt5_real(simbolo)
            info_tick = obtener_precio_actual(simbolo_real)
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
        except Exception:
            pass