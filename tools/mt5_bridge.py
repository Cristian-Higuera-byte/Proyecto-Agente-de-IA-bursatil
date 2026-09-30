"""
mt5_bridge.py
---------------
Módulo encargado de la comunicación directa con MetaTrader 5 (MT5)
para extracción de datos en tiempo real, histórico y ejecución de órdenes.
"""

import os
from datetime import datetime
from typing import Optional

import MetaTrader5 as mt5  # type: ignore[import-untyped]
import pandas as pd  # type: ignore[import-untyped]
from dotenv import load_dotenv

load_dotenv()

# Ruta al ejecutable del terminal MetaTrader 5.
# Se puede sobrescribir en el .env con MT5_PATH; si no, usa la ruta estándar.
RUTA_TERMINAL_MT5 = os.getenv(
    "MT5_PATH",
    r"C:\Program Files\MetaTrader 5\terminal64.exe",
)


def inicializar_mt5(
    login: Optional[int] = None,
    password: Optional[str] = None,
    server: Optional[str] = None,
) -> bool:
    """
    Inicializa y conecta con el terminal de MetaTrader 5.
    Se engancha al terminal indicado en RUTA_TERMINAL_MT5 (lo abre si está cerrado).
    Si no se pasan credenciales, usa la cuenta ya logueada en el terminal.
    """
    if not mt5.initialize(path=RUTA_TERMINAL_MT5):
        print(f"Error al inicializar MT5, código de error: {mt5.last_error()}")
        return False

    # Si se proporcionan credenciales específicas de cuenta
    if login and password and server:
        autorizado = mt5.login(login, password=password, server=server)
        if not autorizado:
            print(f"Falló el login en MT5, código de error: {mt5.last_error()}")
            return False

    return True

def cerrar_mt5():
    """Cierra la conexión con MetaTrader 5."""
    mt5.shutdown()


# ---------------------------------------------------------------------------
# Resolvedor de símbolos entre brókers
# ---------------------------------------------------------------------------
# Distintos brókers nombran el MISMO instrumento distinto: el de Emilio
# (MEXAtlantic) usa sufijo "..." en Forex/metales (EURUSD..., XAUUSD...),
# otros lo traen limpio (EURUSD) o con sufijos como ".m"/".pro"/".c".
# Este resolvedor toma un símbolo "pedido" y devuelve el nombre REAL que
# exista en el terminal actual, para que el mismo código funcione en ambos.
_INDICE_SIMBOLOS: Optional[dict] = None


def _core_simbolo(name: str) -> str:
    """Núcleo comparable de un símbolo: sin '...' ni sufijos de bróker/bolsa."""
    s = (name or "").upper().strip().replace("...", "")
    if "." in s:  # p. ej. AAPL.OQ, EURUSD.m, BTCUSD.pro
        base, suf = s.rsplit(".", 1)
        if suf.isalnum() and 1 <= len(suf) <= 4:
            s = base
    return s


def _indice_local(refrescar: bool = False) -> dict:
    """Índice del terminal actual: nombres exactos + mapa por 'núcleo'. Cacheado."""
    global _INDICE_SIMBOLOS
    if _INDICE_SIMBOLOS is not None and not refrescar:
        return _INDICE_SIMBOLOS
    exact: set = set()
    core: dict = {}
    try:
        for s in (mt5.symbols_get() or []):
            exact.add(s.name)
            core.setdefault(_core_simbolo(s.name), s.name)
    except Exception:
        pass
    _INDICE_SIMBOLOS = {"exact": exact, "core": core}
    return _INDICE_SIMBOLOS


def resolver_simbolo(symbol: str) -> str:
    """Devuelve el nombre real del símbolo en el terminal actual.
    1) si existe exacto, se usa; 2) si no, se busca por 'núcleo'
    (EURUSD... <-> EURUSD <-> EURUSD.m); 3) si no hay match, se retorna igual."""
    if not symbol:
        return symbol
    idx = _indice_local()
    if symbol in idx["exact"]:
        return symbol
    return idx["core"].get(_core_simbolo(symbol), symbol)

def obtener_info_cuenta() -> dict:
    """Retorna el balance, equity y margen de la cuenta activa."""
    cuenta = mt5.account_info()
    if cuenta is None:
        return {"error": "No se pudo obtener información de la cuenta MT5"}
    
    return {
        "login": cuenta.login,
        "balance": cuenta.balance,
        "equity": cuenta.equity,
        "profit": cuenta.profit,
        "margin_free": cuenta.margin_free,
        "currency": cuenta.currency
    }

def obtener_precio_actual(symbol: str) -> dict:
    """Obtiene el precio Bid, Ask y último tick de un símbolo.
    Resuelve el nombre real en el terminal actual (con o sin '...')."""
    symbol = resolver_simbolo(symbol)
    # Asegurar que el símbolo esté visible en la observación de mercado
    mt5.symbol_select(symbol, True)
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return {"error": f"No se pudo obtener el tick para {symbol}"}
    
    return {
        "symbol": symbol,
        "bid": tick.bid,
        "ask": tick.ask,
        "last": tick.last,
        "time": datetime.fromtimestamp(tick.time).strftime('%Y-%m-%d %H:%M:%S')
    }

def obtener_datos_historicos(symbol: str, timeframe=mt5.TIMEFRAME_H1, n_velas: int = 100) -> pd.DataFrame:
    """
    Descarga datos históricos OHLCV de MT5 y los retorna como un DataFrame de Pandas
    listos para graficar o analizar.
    """
    symbol = resolver_simbolo(symbol)
    mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n_velas)
    
    if rates is None or len(rates) == 0:
        return pd.DataFrame()

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

def ejecutar_orden_mercado(symbol: str, tipo: str, volumen: float, sl: float = 0.0, tp: float = 0.0) -> dict:
    """
    Ejecuta una orden de compra o venta a mercado en MT5.
    tipo: 'BUY' o 'SELL'
    """
    mt5.symbol_select(symbol, True)
    sim_info = mt5.symbol_info(symbol)
    if sim_info is None:
        return {"error": f"Símbolo {symbol} no encontrado en MT5"}

    tipo_orden = mt5.ORDER_TYPE_BUY if tipo.upper() == 'BUY' else mt5.ORDER_TYPE_SELL
    precio = sim_info.ask if tipo.upper() == 'BUY' else sim_info.bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volumen,
        "type": tipo_orden,
        "price": precio,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": 234000,
        "comment": "Terminal IA Agent - Criss",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    resultado = mt5.order_send(request)
    if resultado.retcode != mt5.TRADE_RETCODE_DONE:
        return {"error": f"Fallo al enviar orden, retcode={resultado.retcode}"}

    return {
        "status": "success",
        "order": resultado.order,
        "price": resultado.price,
        "volume": resultado.volume,
        "symbol": symbol
    }