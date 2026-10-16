"""Velas OHLC de MT5 en el formato que espera Lightweight Charts."""
from herramientas.puente_mt5 import inicializar_mt5, obtener_datos_historicos
from proveedores.selector_mt5 import mt5  # type: ignore[import-untyped]

from .constantes import CANDADO_MT5, TF_MAP


def obtener_velas(simbolo: str, tf: str, n: int) -> list:
    """Devuelve una lista de velas OHLC de MT5 en formato JSON para Lightweight Charts."""
    with CANDADO_MT5:
        inicializar_mt5()
        df = obtener_datos_historicos(simbolo, timeframe=TF_MAP.get(tf, mt5.TIMEFRAME_H1), n_velas=n)
    if df.empty:
        return []
    velas = []
    for tiempo, fila in df.iterrows():
        velas.append({
            "time": int(tiempo.timestamp()),
            "open": round(float(fila["open"]), 5),
            "high": round(float(fila["high"]), 5),
            "low": round(float(fila["low"]), 5),
            "close": round(float(fila["close"]), 5),
            "volume": float(fila["tick_volume"]),
            "spread": float(fila["spread"]) if "spread" in fila.index else 0.0,   # puntos; lo usa el backtest
        })
    return velas
