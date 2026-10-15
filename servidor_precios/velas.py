# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ------------------------------------- INICIO Piña y Jara velas .PY ------------------------------------
# -------------------------------------------------------------------------------------------------------

"""Velas OHLC de MT5 en el formato que espera Lightweight Charts.

Expone `obtener_velas`, que usan las rutas GET /velas y /ultima de manejador.py.
Todas las lecturas a MT5 se serializan con CANDADO_MT5 (la API no es thread-safe).
"""
from herramientas.puente_mt5 import inicializar_mt5, obtener_datos_historicos
import MetaTrader5 as mt5  # type: ignore[import-untyped]

from .constantes import CANDADO_MT5, TF_MAP


def obtener_velas(simbolo: str, tf: str, n: int) -> list:
    """Devuelve una lista de velas OHLC de MT5 en formato JSON para Lightweight Charts.

    Recibe el símbolo, la temporalidad como texto (clave de TF_MAP; si no existe se usa H1)
    y la cantidad `n` de velas. Cada vela es un dict con time (segundos UNIX), open, high,
    low, close (redondeados a 5 decimales), volume (tick_volume) y spread (puntos, 0.0 si
    el dato no existe). Devuelve una lista vacía si MT5 no entrega datos.
    Efectos: inicializa MT5 y consulta el histórico bajo CANDADO_MT5.
    """
    # Consulta el histórico con el terminal bloqueado para otros hilos
    with CANDADO_MT5:
        inicializar_mt5()
        df = obtener_datos_historicos(simbolo, timeframe=TF_MAP.get(tf, mt5.TIMEFRAME_H1), n_velas=n)
    # Sin datos (símbolo inválido o mercado sin histórico): lista vacía
    if df.empty:
        return []
    # Convierte cada fila del DataFrame al formato JSON del gráfico
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


# -------------------------------------------------------------------------------------------------------
# -------------------------------------- FIN Piña y Jara velas .PY --------------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
