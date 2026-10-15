"""Puerto, versión de la API, temporalidades, intervalos del motor y candado de MT5."""
import threading

import MetaTrader5 as mt5  # type: ignore[import-untyped]

PUERTO = 8000
# Versión de la API. Se sube cuando cambian rutas o datos que usa el navegador:
# el gráfico la compara (GET /salud) y avisa si este proceso quedó desactualizado.
# 3 = órdenes pendientes con caducidad (POST /orden/modificar con "caducidad").
# 4 = stop dinámico (trailing): motor que mueve el SL + flag "tr" por posición en el feed.
# 5 = OCO (One-Cancels-the-Other): motor que cancela la pata sobrante + flag "oco" por orden.
# 6 = POST /mercado (orden a mercado desde los botones VENDER/COMPRAR del gráfico en pantalla completa).
VERSION_API = 6

# Temporalidades soportadas (igual que el selector del dashboard)
TF_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
    "MN1": mt5.TIMEFRAME_MN1,
}

# Todas las llamadas a MT5 de ESTE proceso pasan por aquí (la API no es thread-safe
# y el servidor atiende cada petición en su propio hilo).
CANDADO_MT5 = threading.RLock()

INTERVALO_TICKS = 0.25       # s entre lecturas de ticks (4 por segundo)
INTERVALO_CUENTA = 1.0       # s entre lecturas de saldo / P-G
INTERVALO_EQUITY = 60.0      # s entre snapshots de equity (para el drawdown real)
TTL_REFERENCIA = 300         # s que se reutiliza el cierre del día anterior
TTL_SUSCRIPCION = 60         # s sin clientes pidiendo un símbolo -> se deja de leer
PING_SSE = 15                # s sin cambios -> comentario keep-alive

TTL_SIMBOLOS = 300   # s que se reutiliza el catálogo de símbolos
