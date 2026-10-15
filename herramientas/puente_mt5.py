# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ---------------------------------- INICIO Piña y Jara puente_mt5 .PY ----------------------------------
# -------------------------------------------------------------------------------------------------------

"""
puente_mt5.py
-------------
Módulo encargado de la comunicación directa con MetaTrader 5 (MT5) para
extracción de datos en tiempo real, histórico y ejecución de órdenes. Es la
única capa del proyecto que habla con la API de Python de MT5; el resto de la
aplicación (aplicacion.py, consola_agente.py, las herramientas del agente) la
consume a través de las funciones públicas de este archivo.

Qué ofrece:
  - Conexión robusta al terminal: busca la ruta del terminal64.exe (primero
    MT5_PATH del .env, luego el terminal abierto y por último las carpetas
    típicas de instalación), limita cada intento a 10 s y espera 15 s entre
    reintentos fallidos para no congelar la app.
  - Verificación de que el terminal tenga una cuenta con sesión iniciada (si no,
    MT5 "conecta" pero no entrega precios ni saldo).
  - Resolvedor de símbolos entre brókers (alias XAUUSD <-> GOLD, US30 <->
    US30Cash, sufijos "...", ".m", ".pro", etc.).
  - Lectura de cuenta, posiciones, historial de cierres, precios, velas y DOM.
  - Envío de órdenes a mercado y pendientes, cierre, modificación de SL/TP y
    cancelación de pendientes. Todo acceso a MT5 se serializa con `MT5_LOCK`
    porque la API no es segura entre hilos.

SI AÚN NO CONECTA, REVISAR:
  - El terminal MT5 abierto y con la cuenta iniciada (abajo a la derecha debe
    mostrar ping/conexión, no "Sin conexión").
  - En MT5: Herramientas > Opciones > Asesores Expertos > "Permitir trading
    algorítmico" (necesario para enviar órdenes; para leer precios no).
  - Python de 64 bits (el paquete MetaTrader5 no funciona con Python de 32 bits).
  - Poner la ruta exacta en el .env, por ejemplo:
        MT5_PATH=C:\\Program Files\\XM Global SC MT5 Terminal\\terminal64.exe
    (la ruta exacta aparece en la consola al iniciar la app).

Nota histórica: se evita deliberadamente `mt5.initialize()` sin ruta, porque
produce "IPC timeout" y deja la app esperando hasta 60 s en cada llamada.
"""

import glob
import os
import subprocess
import threading
import time
from datetime import datetime
from typing import Optional

import MetaTrader5 as mt5  # type: ignore[import-untyped]
import pandas as pd  # type: ignore[import-untyped]
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Candado GLOBAL de acceso a MetaTrader 5
# ---------------------------------------------------------------------------
# La API de Python de MT5 NO es segura entre hilos: serializa el acceso.
# Es reentrante (RLock) para que una función con el candado pueda llamar a otra
# que también lo toma (p. ej. inicializar_mt5 dentro de obtener_posiciones).
MT5_LOCK = threading.RLock()
# Alias histórico: el candado de órdenes es el mismo que el de lectura, así una
# orden nunca se mezcla con otra consulta concurrente.
_ORDER_LOCK = MT5_LOCK

# Ruta al ejecutable del terminal MetaTrader 5 (configurable por .env)
RUTA_TERMINAL_MT5 = os.getenv("MT5_PATH", "").strip().strip('"')

_TIMEOUT_MS = 10_000          # máximo por intento de conexión
_REINTENTO_S = 15             # espera entre reintentos si no conecta
# Marca de tiempo (epoch, segundos) del último intento de conexión fallido; 0.0 = ninguno.
_ultimo_fallo = 0.0
# Ruta del terminal con el que se logró conectar (solo para mensajes de consola).
_ruta_conectada: Optional[str] = None


def _terminal_en_ejecucion() -> list:
    """
    Devuelve las rutas de los terminal64.exe de MetaTrader 5 que están abiertos ahora.

    Consulta los procesos mediante PowerShell (solo Windows, sin mostrar ventana,
    máximo 8 s). Si PowerShell no existe o falla devuelve una lista vacía. Sirve
    para conectarse al terminal que el usuario ya tiene abierto.
    """
    try:
        # Pide a PowerShell la ruta de cada proceso terminal64 en ejecución.
        salida = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-Process terminal64 -ErrorAction SilentlyContinue | "
             "Select-Object -ExpandProperty Path"],
            capture_output=True, text=True, timeout=8,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout
        return [l.strip() for l in salida.splitlines() if l.strip().lower().endswith("terminal64.exe")]
    except Exception:
        return []


def _rutas_candidatas() -> list:
    """
    Construye la lista ordenada de rutas posibles del terminal MT5, sin repetidos.

    Orden de prioridad: MT5_PATH del .env, terminales abiertos y las carpetas
    típicas de instalación (Program Files, Program Files (x86) y datos de
    MetaQuotes). Solo conserva rutas que existan como archivo.
    """
    rutas = []
    if RUTA_TERMINAL_MT5:
        rutas.append(RUTA_TERMINAL_MT5)
    rutas += _terminal_en_ejecucion()
    # Busca instalaciones típicas: <base>/<carpeta del bróker>/terminal64.exe
    for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                 os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                 os.path.expandvars(r"%APPDATA%\MetaQuotes\Terminal")):
        rutas += glob.glob(os.path.join(base, "*", "terminal64.exe"))
    # Elimina duplicados (comparando rutas normalizadas) y descarta las inexistentes.
    vistas, unicas = set(), []
    for r in rutas:
        k = os.path.normcase(os.path.abspath(r))
        if k not in vistas and os.path.isfile(r):
            vistas.add(k)
            unicas.append(r)
    return unicas


def inicializar_mt5(
    login: Optional[int] = None,
    password: Optional[str] = None,
    server: Optional[str] = None,
) -> bool:
    """
    Inicializa y conecta con el terminal de MetaTrader 5 de forma segura.
    - Si ya hay conexión activa, no hace nada (rápido).
    - Si no, prueba las rutas candidatas (máx. 10 s cada una).
    - Si falla, no reintenta hasta pasados 15 s (para no congelar la app).

    Parámetros opcionales: login, password y server permiten iniciar sesión
    explícitamente en una cuenta; si se omiten se usa la cuenta ya iniciada en
    el terminal. Devuelve True si hay conexión con el terminal (aunque no tenga
    cuenta iniciada, caso en que solo avisa por consola) y False si no se pudo
    conectar. Efectos secundarios: llamadas a MT5, mensajes por consola y
    actualización de `_ultimo_fallo` y `_ruta_conectada`.
    """
    global _ultimo_fallo, _ruta_conectada
    with MT5_LOCK:
        # Ya conectado: evita llamadas redundantes
        if mt5.terminal_info() is not None:
            return True

        # Anti-congelamiento: tras un fallo reciente no se reintenta todavía.
        if time.time() - _ultimo_fallo < _REINTENTO_S:
            return False

        # Busca dónde está instalado/abierto el terminal.
        rutas = _rutas_candidatas()
        if not rutas:
            print("[MT5] No se encontró ningún terminal64.exe. ¿Está instalado MetaTrader 5? "
                  "Pon la ruta en el .env:  MT5_PATH=C:\\...\\terminal64.exe")
            _ultimo_fallo = time.time()
            return False

        # Prueba cada ruta hasta que una conecte; el else del for se ejecuta si ninguna sirvió.
        for ruta in rutas:
            if mt5.initialize(path=ruta, timeout=_TIMEOUT_MS):
                _ruta_conectada = ruta
                break
            print(f"[MT5] No se pudo conectar con {ruta}: {mt5.last_error()}")
        else:
            print("[MT5] Sin conexión. Revisa que el terminal esté ABIERTO y con la cuenta "
                  "iniciada, y que Python sea de 64 bits.")
            _ultimo_fallo = time.time()
            return False

        # Credenciales explícitas (opcional)
        if login and password and server:
            if not mt5.login(int(login), password=password, server=server):
                print(f"[MT5] Falló el login de la cuenta {login}: {mt5.last_error()}")
                _ultimo_fallo = time.time()
                return False

        # Verifica que el terminal tenga cuenta; sin ella no hay precios ni saldo.
        cuenta = mt5.account_info()
        if cuenta is None:
            print(f"[MT5] Conectado a {_ruta_conectada}, pero el terminal NO tiene una cuenta "
                  "iniciada. Inicia sesión en MT5 (Archivo > Iniciar sesión en cuenta).")
        else:
            print(f"[MT5] Conectado: {cuenta.login} @ {cuenta.server} ({_ruta_conectada})")
        return True


def cerrar_mt5():
    """Cierra la conexión con el terminal MetaTrader 5 (mt5.shutdown) bajo el candado global."""
    with MT5_LOCK:
        mt5.shutdown()


# ---------------------------------------------------------------------------
# Resolvedor de símbolos entre brókers
# ---------------------------------------------------------------------------
# Distintos brókers nombran el MISMO instrumento distinto: MEXAtlantic usa
# sufijo "..." (EURUSD..., XAUUSD...), XM los trae limpios (EURUSD) pero
# renombra oro/índices (GOLD, US30Cash), y otros usan ".m"/".pro"/".c".
# Caché del índice de símbolos del terminal: {"exact": set de nombres, "core": núcleo -> nombre real}.
# None = aún no construido (o el último intento salió vacío y se reintentará).
_INDICE_SIMBOLOS: Optional[dict] = None

# Grupos de nombres equivalentes entre brókers (en mayúsculas, sin sufijos).

_ALIAS_GRUPOS = [
    ["XAUUSD", "GOLD"],
    ["XAGUSD", "SILVER"],
    ["US30", "US30CASH", "DJ30", "WS30", "DOWJONES"],
    ["NAS100", "US100", "US100CASH", "USTEC", "NDX100"],
    ["US500", "SPX500", "US500CASH", "SP500"],
    ["USOIL", "WTI", "OILCASH", "XTIUSD", "OIL"],
    ["UKOIL", "BRENT", "BRENTCASH", "XBRUSD", "UKOUSD"],
    ["UK100", "UK100CASH", "FTSE100"],
    ["GER40", "DE40", "GER40CASH", "DAX40"],
]
# Diccionario inverso: nombre -> grupo completo de alias, para búsqueda directa.
_ALIAS = {n: grupo for grupo in _ALIAS_GRUPOS for n in grupo}


def _nucleo_simbolo(name: str) -> str:
    """
    Devuelve el núcleo comparable de un símbolo, sin '...' ni sufijos de bróker/bolsa.

    Pasa a mayúsculas, quita "...", '#', el sufijo "MICRO" de cuentas micro y un
    sufijo alfanumérico de hasta 4 caracteres tras el último punto (.OQ, .m,
    .pro). Así 'EURUSD...', 'EURUSD.m' y 'EURUSDmicro' dan 'EURUSD'.
    """
    s = (name or "").upper().strip().replace("...", "").strip("#")
    if s.endswith("MICRO"):          # XM cuentas Micro: EURUSDmicro
        s = s[:-5]
    if "." in s:                     # AAPL.OQ, EURUSD.m, BTCUSD.pro
        base, suf = s.rsplit(".", 1)
        if suf.isalnum() and 1 <= len(suf) <= 4:
            s = base
    return s


def _indice_local(refrescar: bool = False) -> dict:
    """
    Devuelve (y cachea) el índice de símbolos disponibles en el terminal actual.

    Estructura: {"exact": conjunto de nombres exactos, "core": núcleo -> primer
    nombre real con ese núcleo}. Con `refrescar=True` reconstruye la caché. No
    guarda un índice vacío (p. ej. sin conexión), de modo que se reintenta en la
    próxima llamada. Efecto secundario: llamada a mt5.symbols_get y escritura de
    `_INDICE_SIMBOLOS`.
    """
    global _INDICE_SIMBOLOS
    if _INDICE_SIMBOLOS is not None and not refrescar:
        return _INDICE_SIMBOLOS
    exact: set = set()
    core: dict = {}
    try:
        if not inicializar_mt5():
            return {"exact": exact, "core": core}
        with MT5_LOCK:
            simbolos = mt5.symbols_get() or []
        for s in simbolos:
            exact.add(s.name)
            core.setdefault(_nucleo_simbolo(s.name), s.name)
    except Exception:
        pass
    if not exact:
        return {"exact": exact, "core": core}
    _INDICE_SIMBOLOS = {"exact": exact, "core": core}
    return _INDICE_SIMBOLOS


def resolver_simbolo(symbol: str) -> str:
    """
    Traduce un nombre de símbolo al nombre real que usa el bróker conectado.

    Busca en este orden: coincidencia exacta, coincidencia por núcleo (ignora
    sufijos) y alias equivalentes (XAUUSD <-> GOLD, etc.). Si nada coincide
    devuelve el símbolo original sin cambios.
    """
    if not symbol:
        return symbol
    idx = _indice_local()
    if symbol in idx["exact"]:
        return symbol
    core = _nucleo_simbolo(symbol)
    if core in idx["core"]:
        return idx["core"][core]
    for alias in _ALIAS.get(core, []):
        if alias in idx["core"]:
            return idx["core"][alias]
    return symbol


def obtener_info_cuenta() -> dict:
    """
    Devuelve los datos de la cuenta activa: login, nombre, servidor, tipo
    (Real/Concurso/Demo según trade_mode), balance, equity, profit, margen,
    margen libre, nivel de margen, crédito, apalancamiento y moneda.

    Si no hay conexión o la cuenta no está iniciada devuelve {"error": ...}.
    """
    with MT5_LOCK:
        if not inicializar_mt5():
            return {"error": "Sin conexión con MT5"}
        cuenta = mt5.account_info()
    if cuenta is None:
        return {"error": "No se pudo obtener información de la cuenta MT5 (¿cuenta sin iniciar?)"}

    # trade_mode de MT5: 0 = demo, 1 = concurso, 2 = real.
    modo = getattr(cuenta, "trade_mode", 0)
    tipo = "Real" if modo == 2 else ("Concurso" if modo == 1 else "Demo")
    return {
        "login": cuenta.login,
        "nombre": getattr(cuenta, "name", ""),
        "servidor": getattr(cuenta, "server", ""),
        "tipo": tipo,
        "balance": cuenta.balance,
        "equity": cuenta.equity,
        "profit": cuenta.profit,
        "margin": getattr(cuenta, "margin", 0.0),
        "margin_free": cuenta.margin_free,
        "margin_level": getattr(cuenta, "margin_level", 0.0),
        "credit": getattr(cuenta, "credit", 0.0),
        "leverage": getattr(cuenta, "leverage", 0),
        "currency": cuenta.currency,
    }


def obtener_posiciones() -> list:
    """
    Devuelve las posiciones abiertas de la cuenta (para la 'Cartera').

    Cada elemento es un diccionario con ticket, symbol, tipo ("Compra"/"Venta"),
    volumen, precios de apertura y actual, profit, swap, sl, tp y tiempo de
    apertura. Devuelve lista vacía si no hay conexión o ocurre un error.
    """
    try:
        with MT5_LOCK:
            if not inicializar_mt5():
                return []
            posiciones = mt5.positions_get()
    except Exception:
        posiciones = None
    # Convierte cada tupla de MT5 en un diccionario simple.
    salida = []
    for p in (posiciones or []):
        salida.append({
            "ticket": p.ticket,
            "symbol": p.symbol,
            "tipo": "Compra" if p.type == 0 else "Venta",
            "volumen": p.volume,
            "precio_apertura": p.price_open,
            "precio_actual": p.price_current,
            "profit": p.profit,
            "swap": p.swap,          # la Cartera muestra P/G neto (profit + swap)
            "sl": p.sl,              # 0.0 si no tiene Stop Loss
            "tp": p.tp,              # 0.0 si no tiene Take Profit
            "tiempo": p.time,        # epoch de apertura (hora del servidor del bróker)
        })
    return salida


def obtener_historial(dias: int = 90, limite: int = 100) -> list:
    """Operaciones CERRADAS de la cuenta (para el historial de Inicio).

    Parámetros: `dias` (ventana hacia atrás desde ahora) y `limite` (máximo de
    filas devueltas). Cada elemento trae ticket, symbol, tipo, volumen,
    precio_cierre, pg (neto) y fecha (epoch). Devuelve lista vacía sin conexión.

    En MT5 cada cierre de posición es un 'deal' con entry == DEAL_ENTRY_OUT, que
    es el que trae el P/G realizado. El P/G neto se arma igual que en la Cartera:
    profit + swap + comisión. Un cierre tipo SELL cerró una COMPRA (y viceversa).
    Devuelve del más reciente al más antiguo, recortado a 'limite'.
    """
    from datetime import timedelta
    # El servidor del bróker va en otra zona (XM = GMT+3): una operación recién
    # cerrada queda con marca de tiempo "por delante" de la hora local y se cortaría
    # del rango. Por eso el tope superior va +1 día (incluye siempre lo recién cerrado).
    try:
        with MT5_LOCK:
            if not inicializar_mt5():
                return []
            deals = mt5.history_deals_get(datetime.now() - timedelta(days=dias),
                                          datetime.now() + timedelta(days=1))
    except Exception:
        deals = None
    # Filtra solo los deals de cierre y calcula el P/G neto de cada uno.
    salida = []
    for d in (deals or []):
        if d.entry != mt5.DEAL_ENTRY_OUT:        # solo cierres (traen el P/G realizado)
            continue
        neto = d.profit + d.swap + d.commission + getattr(d, "fee", 0.0)
        salida.append({
            "ticket": d.ticket,
            "symbol": d.symbol,
            "tipo": "Compra" if d.type == mt5.DEAL_TYPE_SELL else "Venta",
            "volumen": d.volume,
            "precio_cierre": d.price,
            "pg": neto,
            "fecha": d.time,                     # epoch (hora del servidor del bróker)
        })
    # Ordena del más reciente al más antiguo y recorta al límite pedido.
    salida.sort(key=lambda x: x["fecha"], reverse=True)
    return salida[:limite]


def especs_posicion(ticket: int) -> dict:
    """Datos del contrato de una posición para el panel de TP/SL de la Cartera:
    k (valor de 1 unidad de precio por lote, en la moneda de la cuenta), dígitos,
    point, distancia mínima del bróker (stops_level) y Bid/Ask en vivo. Permite
    validar la distancia mínima y convertir un objetivo en 'Cantidad' ($) a precio.

    Recibe el ticket de la posición. Devuelve además srv_now (hora del servidor,
    para calcular el desfase horario), precio de apertura, tipo y volumen.
    Devuelve {} si no hay conexión, la posición no existe o no hay info del símbolo.
    """
    with MT5_LOCK:
        if not inicializar_mt5():
            return {}
        pos = mt5.positions_get(ticket=int(ticket))
        if not pos:
            return {}
        p = pos[0]
        info = mt5.symbol_info(p.symbol)
        tick = mt5.symbol_info_tick(p.symbol)
    if not info:
        return {}
    # k = valor monetario de mover 1 unidad de precio con 1 lote (tick_value / tick_size).
    tsize = getattr(info, "trade_tick_size", 0.0) or 0.0
    k = (info.trade_tick_value / tsize) if tsize else 0.0
    return {
        "k": k,
        "digitos": int(getattr(info, "digits", 5) or 5),
        "point": float(getattr(info, "point", 0.0) or 0.0),
        "stops_level": int(getattr(info, "trade_stops_level", 0) or 0),
        "bid": float(getattr(tick, "bid", 0.0) or 0.0),
        "ask": float(getattr(tick, "ask", 0.0) or 0.0),
        "srv_now": float(getattr(tick, "time", 0.0) or 0.0),   # epoch del servidor (para desfase horario)
        "precio_apertura": float(p.price_open),
        "tipo": "Compra" if p.type == 0 else "Venta",
        "volumen": float(p.volume),
    }


def obtener_precio_actual(symbol: str) -> dict:
    """
    Obtiene el precio Bid, Ask y último de un símbolo.

    Resuelve el nombre al del bróker, lo activa en Market Watch y lee el último
    tick; si el tick viene vacío usa bid/ask de symbol_info como respaldo.
    Devuelve {symbol, bid, ask, last, time} o {"error": ...}.
    """
    symbol = resolver_simbolo(symbol)
    with MT5_LOCK:
        if not inicializar_mt5():
            return {"error": "Sin conexión con MT5"}
        mt5.symbol_select(symbol, True)
        tick = mt5.symbol_info_tick(symbol)

    if tick is not None and (tick.bid or tick.ask):
        return {
            "symbol": symbol,
            "bid": tick.bid,
            "ask": tick.ask,
            "last": tick.last,
            "time": datetime.fromtimestamp(tick.time).strftime('%Y-%m-%d %H:%M:%S'),
        }

    # Respaldo: bid/ask de symbol_info si el tick viene vacío momentáneamente
    with MT5_LOCK:
        info = mt5.symbol_info(symbol)
    if info is not None:
        try:
            bid, ask, last = float(info.bid), float(info.ask), float(info.last)
        except (AttributeError, TypeError, ValueError):
            bid = ask = last = 0.0
        if bid or ask:
            return {
                "symbol": symbol,
                "bid": bid,
                "ask": ask,
                "last": last,
                "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
    return {"error": f"No se pudo obtener el precio para {symbol}"}


def obtener_datos_historicos(symbol: str, timeframe=mt5.TIMEFRAME_H1, n_velas: int = 100) -> pd.DataFrame:
    """
    Descarga las últimas `n_velas` velas OHLCV del símbolo en el `timeframe` dado.

    Devuelve un DataFrame de pandas indexado por `time` (datetime), o un
    DataFrame vacío si no hay conexión ni datos. Activa el símbolo en Market Watch.
    """
    symbol = resolver_simbolo(symbol)
    with MT5_LOCK:
        if not inicializar_mt5():
            return pd.DataFrame()
        mt5.symbol_select(symbol, True)
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n_velas)

    if rates is None or len(rates) == 0:
        return pd.DataFrame()

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df


def obtener_velas_rango(symbol: str, ts_desde: float, ts_hasta: float) -> list:
    """Velas OHLC que cubren [ts_desde, ts_hasta] (epoch), para el mini-gráfico del
    Trading Journal. Elige el timeframe según la duración para que haya ~40-120 velas
    y añade un margen a cada lado. Devuelve [{t,o,h,l,c}, ...] (vieja → nueva).
    Recibe el símbolo y los límites del rango como epoch en segundos; devuelve
    lista vacía si no hay conexión o datos."""
    from datetime import datetime as _dt
    # Duración del rango (mínimo 1 min) y margen de relleno a cada lado.
    dur = max(60.0, float(ts_hasta) - float(ts_desde))
    pad = dur * 0.35 + 300
    d0, d1 = float(ts_desde) - pad, float(ts_hasta) + pad
    # timeframe objetivo ≈ ventana/60 velas
    objetivo = (d1 - d0) / 60.0
    escala = [(60, mt5.TIMEFRAME_M1), (300, mt5.TIMEFRAME_M5), (900, mt5.TIMEFRAME_M15),
              (3600, mt5.TIMEFRAME_H1), (14400, mt5.TIMEFRAME_H4), (86400, mt5.TIMEFRAME_D1)]
    # Escoge el primer timeframe cuya duración alcance el objetivo (o el mayor).
    tf = escala[0][1]
    for seg, cod in escala:
        tf = cod
        if seg >= objetivo:
            break
    symbol = resolver_simbolo(symbol)
    with MT5_LOCK:
        if not inicializar_mt5():
            return []
        mt5.symbol_select(symbol, True)
        rates = mt5.copy_rates_range(symbol, tf, _dt.fromtimestamp(d0), _dt.fromtimestamp(d1))
    if rates is None or len(rates) == 0:
        return []
    # Normaliza cada vela a un diccionario simple.
    return [{"t": int(r["time"]), "o": float(r["open"]), "h": float(r["high"]),
             "l": float(r["low"]), "c": float(r["close"])} for r in rates]


def _modo_llenado(sim_info):
    """
    Elige el modo de llenado de órdenes que soporta el símbolo (FOK, IOC o RETURN).

    Evita el error 'Unsupported filling mode'. Recibe el `symbol_info` y
    devuelve la constante ORDER_FILLING_* de MT5.
    """
    # filling_mode es una máscara: bit 1 = FOK permitido, bit 2 = IOC permitido.
    fm = getattr(sim_info, "filling_mode", 0)
    if fm & 1:
        return mt5.ORDER_FILLING_FOK
    if fm & 2:
        return mt5.ORDER_FILLING_IOC
    return mt5.ORDER_FILLING_RETURN


def ejecutar_orden_mercado(symbol: str, tipo: str, volumen: float, sl: float = 0.0, tp: float = 0.0) -> dict:
    """
    Ejecuta una orden de compra o venta a mercado en MT5. tipo: 'BUY' o 'SELL'.

    Recibe símbolo, volumen en lotes y SL/TP opcionales (0 = sin nivel).
    Devuelve {"status": "success", order, price, volume, symbol} o
    {"error": ...}. Efectos secundarios: envía una orden real al broker y, si
    llevaba SL/TP, guarda el plan en el Trading Journal (almacen_diario).
    """
    symbol = resolver_simbolo(symbol)
    with _ORDER_LOCK:
        if not inicializar_mt5():
            return {"error": "Sin conexión con MT5"}
        mt5.symbol_select(symbol, True)
        sim_info = mt5.symbol_info(symbol)
        if sim_info is None:
            return {"error": f"Símbolo {symbol} no encontrado en MT5"}

        # Compra al ask y venta al bid; si no hay tick usa el precio de symbol_info.
        tipo_orden = mt5.ORDER_TYPE_BUY if tipo.upper() == 'BUY' else mt5.ORDER_TYPE_SELL
        tick = mt5.symbol_info_tick(symbol)
        precio = (tick.ask if tipo.upper() == 'BUY' else tick.bid) if tick else \
                 (sim_info.ask if tipo.upper() == 'BUY' else sim_info.bid)

        # Solicitud de operación a mercado (deviation = deslizamiento máximo en puntos;
        # magic identifica las órdenes de esta aplicación).
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volumen),
            "type": tipo_orden,
            "price": precio,
            "deviation": 20,
            "magic": 234000,
            "comment": "Piña & Jara Terminal",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": _modo_llenado(sim_info),
        }
        if sl and sl > 0:
            request["sl"] = float(sl)
        if tp and tp > 0:
            request["tp"] = float(tp)

        # Envía la orden al servidor del bróker.
        resultado = mt5.order_send(request)

    # Interpreta el resultado: None o retcode distinto de DONE es un fallo.
    if resultado is None:
        return {"error": f"order_send devolvió None: {mt5.last_error()}"}
    if resultado.retcode != mt5.TRADE_RETCODE_DONE:
        extra = " (activa 'Algo Trading' en MT5)" if resultado.retcode == 10027 else ""
        return {"error": f"Fallo al enviar orden (retcode {resultado.retcode}): "
                         f"{getattr(resultado, 'comment', '')}{extra}"}

    # Trading Journal (Tanda C): si la orden llevaba SL/TP, se guarda el "plan"
    # (entrada real + SL + TP) ligado a la posición para calcular el R/R planificado.
    # position_id de la posición abierta == ticket de la orden de apertura (resultado.order).
    if (sl and sl > 0) or (tp and tp > 0):
        try:
            from herramientas import almacen_diario
            almacen_diario.guardar_plan(resultado.order, resultado.price, sl, tp,
                                       tipo.upper(), symbol, resultado.volume)
        except Exception:
            pass   # el journal nunca debe hacer fallar una orden

    return {
        "status": "success",
        "order": resultado.order,
        "price": resultado.price,
        "volume": resultado.volume,
        "symbol": symbol,
    }


def colocar_orden_pendiente(symbol: str, tipo: str, volumen: float, precio: float,
                            sl: float = 0.0, tp: float = 0.0,
                            hasta_cancelar: bool = True) -> dict:
    """Orden pendiente "comprar/vender al llegar a este precio" (como XM).
    El tipo se deduce del precio pedido respecto del mercado:
      COMPRA bajo el ask -> BUY_LIMIT · sobre el ask -> BUY_STOP
      VENTA sobre el bid -> SELL_LIMIT · bajo el bid -> SELL_STOP
    hasta_cancelar=True -> vigente hasta cancelarla (GTC); False -> solo hoy (DAY).
    Recibe símbolo, tipo 'BUY'/'SELL', volumen, precio de activación y SL/TP
    opcionales. Devuelve {"status": "success", order, price, volume, symbol,
    tipo} o {"error": ...}. Efecto secundario: crea una orden pendiente real."""
    symbol = resolver_simbolo(symbol)
    with _ORDER_LOCK:
        if not inicializar_mt5():
            return {"error": "Sin conexión con MT5"}
        mt5.symbol_select(symbol, True)
        sim_info = mt5.symbol_info(symbol)
        tick = mt5.symbol_info_tick(symbol)
        if sim_info is None or tick is None:
            return {"error": f"Símbolo {symbol} no disponible en MT5"}

        # Precio de referencia (ask en compras, bid en ventas) para decidir limit o stop.
        compra = tipo.upper() == "BUY"
        ref = tick.ask if compra else tick.bid
        if compra:
            tipo_orden = mt5.ORDER_TYPE_BUY_LIMIT if precio < ref else mt5.ORDER_TYPE_BUY_STOP
        else:
            tipo_orden = mt5.ORDER_TYPE_SELL_LIMIT if precio > ref else mt5.ORDER_TYPE_SELL_STOP

        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": float(volumen),
            "type": tipo_orden,
            "price": round(float(precio), int(sim_info.digits)),
            "deviation": 20,
            "magic": 234000,
            "comment": "Piña & Jara Terminal",
            "type_time": mt5.ORDER_TIME_GTC if hasta_cancelar else mt5.ORDER_TIME_DAY,
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }
        if sl and sl > 0:
            request["sl"] = float(sl)
        if tp and tp > 0:
            request["tp"] = float(tp)
        resultado = mt5.order_send(request)

    if resultado is None:
        return {"error": f"order_send devolvió None: {mt5.last_error()}"}
    if resultado.retcode != mt5.TRADE_RETCODE_DONE:
        extra = " (activa 'Algo Trading' en MT5)" if resultado.retcode == 10027 else ""
        return {"error": f"Fallo al colocar la orden pendiente (retcode {resultado.retcode}): "
                         f"{getattr(resultado, 'comment', '')}{extra}"}
    nombres = {mt5.ORDER_TYPE_BUY_LIMIT: "Buy Limit", mt5.ORDER_TYPE_BUY_STOP: "Buy Stop",
               mt5.ORDER_TYPE_SELL_LIMIT: "Sell Limit", mt5.ORDER_TYPE_SELL_STOP: "Sell Stop"}
    return {"status": "success", "order": resultado.order, "price": request["price"],
            "volume": float(volumen), "symbol": symbol, "tipo": nombres.get(tipo_orden, "")}


def cerrar_posicion(ticket: int) -> dict:
    """
    Cierra una posición abierta por su ticket enviando la orden contraria.

    Devuelve {"status": "success", profit (profit + swap al momento de cerrar),
    symbol} o {"error": ...}. Efecto secundario: operación real en el broker.
    """
    with MT5_LOCK:
        if not inicializar_mt5():
            return {"error": "Sin conexión con MT5"}
        pos = mt5.positions_get(ticket=int(ticket))
        if not pos:
            return {"error": f"No se encontró la posición {ticket} (¿ya está cerrada?)"}
        p = pos[0]
        symbol = p.symbol
        mt5.symbol_select(symbol, True)
        sim_info = mt5.symbol_info(symbol)
        tick = mt5.symbol_info_tick(symbol)
        if tick is None and sim_info is None:
            return {"error": f"No hay cotización disponible para {symbol}; no se pudo cerrar la posición {ticket}"}

        # Compra (type 0) se cierra VENDIENDO al bid; venta (type 1) COMPRANDO al ask
        if p.type == mt5.ORDER_TYPE_BUY:
            tipo_cierre = mt5.ORDER_TYPE_SELL
            precio = tick.bid if tick else sim_info.bid
        else:
            tipo_cierre = mt5.ORDER_TYPE_BUY
            precio = tick.ask if tick else sim_info.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(p.volume),
            "type": tipo_cierre,
            "position": int(ticket),
            "price": precio,
            "deviation": 20,
            "magic": 234000,
            "comment": "Cierre Piña & Jara",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": _modo_llenado(sim_info),
        }
        profit = p.profit + getattr(p, "swap", 0.0)
        resultado = mt5.order_send(request)

    if resultado is None:
        return {"error": f"order_send devolvió None: {mt5.last_error()}"}
    if resultado.retcode != mt5.TRADE_RETCODE_DONE:
        extra = " (activa 'Algo Trading' en MT5)" if resultado.retcode == 10027 else ""
        return {"error": f"Fallo al cerrar (retcode {resultado.retcode}): "
                         f"{getattr(resultado, 'comment', '')}{extra}"}
    return {"status": "success", "profit": profit, "symbol": symbol}


def modificar_sltp(ticket: int, sl=None, tp=None) -> dict:
    """Cambia el Stop Loss / Take Profit de una posición abierta.
    None = deja el valor actual; 0 = lo quita. (Líneas arrastrables del gráfico.)
    Redondea a los dígitos del símbolo. Devuelve {"status": "success", ticket,
    sl, tp} o {"error": ...} con el motivo según el retcode de MT5."""
    with MT5_LOCK:
        if not inicializar_mt5():
            return {"error": "Sin conexión con MT5"}
        pos = mt5.positions_get(ticket=int(ticket))
        if not pos:
            return {"error": f"No se encontró la posición {ticket} (¿ya está cerrada?)"}
        p = pos[0]
        info = mt5.symbol_info(p.symbol)
        dig = int(getattr(info, "digits", 5) or 5)
        nuevo_sl = float(p.sl) if sl is None else round(float(sl), dig)
        nuevo_tp = float(p.tp) if tp is None else round(float(tp), dig)
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": p.symbol,
            "position": int(ticket),
            "sl": nuevo_sl,
            "tp": nuevo_tp,
            "magic": 234000,
        }
        resultado = mt5.order_send(request)

    if resultado is None:
        return {"error": f"order_send devolvió None: {mt5.last_error()}"}
    if resultado.retcode != mt5.TRADE_RETCODE_DONE:
        motivo = {10016: "nivel inválido (muy cerca del precio o del lado equivocado)",
                  10027: "activa 'Algo Trading' en MT5",
                  10025: "sin cambios"}.get(resultado.retcode, getattr(resultado, "comment", ""))
        return {"error": f"No se pudo modificar (retcode {resultado.retcode}): {motivo}"}
    return {"status": "success", "ticket": int(ticket), "sl": nuevo_sl, "tp": nuevo_tp}


# Tipo numérico de orden pendiente de MT5 -> nombre legible.
_NOMBRE_PENDIENTE = {2: "Buy Limit", 3: "Sell Limit", 4: "Buy Stop", 5: "Sell Stop"}


def modificar_orden(ticket: int, precio=None, sl=None, tp=None,
                    caducidad=None, expiracion=None) -> dict:
    """Modifica una orden PENDIENTE (precio de entrada, SL, TP y/o caducidad).
    None = conserva el valor actual; 0 en sl/tp = lo quita.
    caducidad: "gtc" | "day" | "specified" (esta última con `expiracion` en
    segundos, hora del SERVIDOR del bróker, como la muestra MT5).
    (Líneas del gráfico y ventana "Modificar orden".)
    Devuelve {"status": "success", ticket, price, sl, tp, tt (tipo de vigencia),
    ex (expiración)} o {"error": ...} con el motivo según el retcode."""
    with MT5_LOCK:
        if not inicializar_mt5():
            return {"error": "Sin conexión con MT5"}
        ords = mt5.orders_get(ticket=int(ticket))
        if not ords:
            return {"error": f"No se encontró la orden {ticket} (¿ya se ejecutó o se canceló?)"}
        o = ords[0]
        info = mt5.symbol_info(o.symbol)
        dig = int(getattr(info, "digits", 5) or 5)
        request = {
            "action": mt5.TRADE_ACTION_MODIFY,
            "order": int(ticket),
            "symbol": o.symbol,
            "price": float(o.price_open) if precio is None else round(float(precio), dig),
            "sl": float(o.sl) if sl is None else round(float(sl), dig),
            "tp": float(o.tp) if tp is None else round(float(tp), dig),
            "type_time": o.type_time,
            "expiration": o.time_expiration,
        }
        if caducidad:
            request["type_time"] = {"gtc": mt5.ORDER_TIME_GTC, "day": mt5.ORDER_TIME_DAY,
                                    "specified": mt5.ORDER_TIME_SPECIFIED}.get(caducidad, o.type_time)
            request["expiration"] = int(expiracion or 0) if caducidad == "specified" else 0
        resultado = mt5.order_send(request)

    if resultado is None:
        return {"error": f"order_send devolvió None: {mt5.last_error()}"}
    if resultado.retcode != mt5.TRADE_RETCODE_DONE:
        motivo = {10015: "precio inválido para este tipo de orden",
                  10022: "fecha de caducidad inválida (o el bróker no la admite)",
                  10016: "nivel inválido (muy cerca del precio o del lado equivocado)",
                  10027: "activa 'Algo Trading' en MT5",
                  10025: "sin cambios"}.get(resultado.retcode, getattr(resultado, "comment", ""))
        return {"error": f"No se pudo modificar la orden (retcode {resultado.retcode}): {motivo}"}
    return {"status": "success", "ticket": int(ticket), "price": request["price"],
            "sl": request["sl"], "tp": request["tp"],
            "tt": int(request["type_time"]), "ex": int(request["expiration"] or 0)}


# Conjunto de símbolos ya suscritos al libro de órdenes con market_book_add.
_DOM_SUSCRITOS = set()   # símbolos con market_book_add ya hecho (se suscribe una vez)


def obtener_dom(symbol: str, niveles: int = 8) -> dict:
    """Profundidad de mercado (DOM) del símbolo: niveles de venta (ask) y compra (bid)
    con su volumen, leídos del LIBRO REAL del bróker (`mt5.market_book_get`).

    Devuelve {"ask":[{price,volume}...], "bid":[...], "disponible":bool}. Requiere que
    el bróker PUBLIQUE el libro para ese símbolo; en Forex/CFD muchas veces no lo hace y
    las listas vienen vacías (disponible=False). La primera lectura tras suscribir puede
    venir vacía (el libro tarda un instante en poblarse); por eso se consulta cada ciclo.
    """
    real = resolver_simbolo(symbol)
    with MT5_LOCK:
        if not inicializar_mt5():
            return {"error": "Sin conexión con MT5"}
        if real not in _DOM_SUSCRITOS:
            if mt5.market_book_add(real):
                _DOM_SUSCRITOS.add(real)
            else:
                return {"ask": [], "bid": [], "disponible": False,
                        "motivo": "El bróker no permite suscribir el libro de este símbolo."}
        libro = mt5.market_book_get(real)

    # Separa los niveles del libro en ventas (ask) y compras (bid).
    asks, bids = [], []
    for it in (libro or []):
        entrada = {"price": float(it.price), "volume": float(it.volume)}
        tipo = int(getattr(it, "type", 0))
        if tipo in (mt5.BOOK_TYPE_SELL, mt5.BOOK_TYPE_SELL_MARKET):      # 1, 3 = venta (ask)
            asks.append(entrada)
        elif tipo in (mt5.BOOK_TYPE_BUY, mt5.BOOK_TYPE_BUY_MARKET):      # 2, 4 = compra (bid)
            bids.append(entrada)
    asks.sort(key=lambda x: x["price"])                 # ask: de menor a mayor precio
    bids.sort(key=lambda x: x["price"], reverse=True)   # bid: de mayor a menor precio
    return {"ask": asks[:niveles], "bid": bids[:niveles],
            "disponible": bool(asks or bids)}


def eliminar_orden(ticket: int) -> dict:
    """
    Cancela una orden PENDIENTE por su ticket.

    Devuelve {"status": "success", ticket, tipo, symbol} o {"error": ...}.
    Efecto secundario: elimina la orden en el broker.
    """
    with MT5_LOCK:
        if not inicializar_mt5():
            return {"error": "Sin conexión con MT5"}
        ords = mt5.orders_get(ticket=int(ticket))
        if not ords:
            return {"error": f"No se encontró la orden {ticket} (¿ya se ejecutó o se canceló?)"}
        o = ords[0]
        resultado = mt5.order_send({"action": mt5.TRADE_ACTION_REMOVE, "order": int(ticket)})

    if resultado is None:
        return {"error": f"order_send devolvió None: {mt5.last_error()}"}
    if resultado.retcode != mt5.TRADE_RETCODE_DONE:
        extra = " (activa 'Algo Trading' en MT5)" if resultado.retcode == 10027 else ""
        return {"error": f"No se pudo cancelar la orden (retcode {resultado.retcode}): "
                         f"{getattr(resultado, 'comment', '')}{extra}"}
    return {"status": "success", "ticket": int(ticket),
            "tipo": _NOMBRE_PENDIENTE.get(o.type, ""), "symbol": o.symbol}


# -------------------------------------------------------------------------------------------------------
# ------------------------------------ FIN Piña y Jara puente_mt5 .PY -----------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
