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

"""Velas OHLC de MT5 o Capital.com en el formato que espera Lightweight Charts, con caché para que cambiar de temporalidad o de activo sea instantáneo.

Expone `obtener_velas` y `obtener_ultima`, que usan las rutas GET /velas y /ultima de manejador.py, y `precalentar`, que el
servidor llama al abrirse el feed para dejar listas las velas de la lista de activos.

Con Capital.com cada lectura es una llamada REST de unos 300-800 ms, y el gráfico pide velas cada vez que se cambia de
temporalidad o de activo. Por eso aquí se guarda en memoria, por (símbolo, temporalidad), la serie de velas más larga que
entrega Capital por petición (1000), ampliable hacia atrás bajo demanda (ver `_profundizar`):
  - Si la serie guardada es de la vela actual y es reciente, se responde al instante, sin tocar la API.
  - Si se venció pero sigue en la misma vela, se responde igual al instante y se refresca en segundo plano.
  - Si ya empezó una vela nueva, se pide solo el tramo final (12 velas), se une a lo guardado y se responde.
  - Al leer un activo se precargan en segundo plano sus otras temporalidades, y al abrir el feed se precarga la
    temporalidad en uso de toda la lista de activos: al cambiar de uno a otro la serie ya está en memoria.
  - Si se piden más velas de las guardadas, se completa el historial con peticiones por tramos hacia atrás
    (herramientas.backends.capital.obtener_datos_anteriores), una sola vez: la serie ampliada queda en memoria (hasta
    `_LARGO_MAX` velas) y el refresco de la última vela no la acorta. El backtest y el replay (más de 1500 velas) esperan a
    la ampliación; el gráfico (hasta 1500) recibe al instante lo que hay y la ampliación se hace en segundo plano.
Las lecturas a Capital.com no se serializan con un candado (a diferencia de MT5, su API REST admite varias a la vez; el
límite de peticiones por segundo lo controla el backend). Con MT5 todo funciona como antes: lecturas bajo CANDADO_MT5, caché
solo para el historial grande del replay (3000 velas o más) y reintentos si el terminal aún descarga el historial.
"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from herramientas.puente_mt5 import PROVEEDOR, inicializar_mt5, obtener_datos_historicos
from proveedores.selector_mt5 import mt5  # type: ignore[import-untyped]

from .constantes import CANDADO_MT5, TF_MAP

# Desde cuántas velas una respuesta se guarda en memoria, cuántos segundos vale y cuántas respuestas se conservan (MT5).
_N_MIN_CACHE = 3000
_TTL_CACHE = 45.0
_MAX_CACHE = 32
# Respuestas guardadas: (símbolo, tf, n) -> (instante, velas).
_CACHE: dict = {}
# Intentos de lectura cuando MT5 devuelve vacío (descarga de historial en curso) y pausa entre ellos, en segundos.
_REINTENTOS = 3
_PAUSA = 0.5

# --- Caché de series para Capital.com -------------------------------------------------------------------------------
_ES_CAPITAL = PROVEEDOR == "capital"
# Velas máximas que entrega Capital.com por petición: la serie guardada tiene ese largo para servir cualquier `n` menor.
_LARGO_SERIE = 1000
# Velas máximas que se guardan por serie tras ampliar el historial, hasta cuántas velas pide el gráfico (a partir de ahí se espera
# a la ampliación: backtest y replay) y segundos que se espera para volver a intentar ampliar una serie cuando Capital ya no
# tenía historial más antiguo.
_LARGO_MAX = 20000
_LARGO_GRAFICO = 1500
_REINTENTO_AGOTADA = 3600.0
# Duración de una vela de cada temporalidad (s), de la más corta a la más larga (el orden se usa para precargar vecinas).
_SEG_TF = {"M1": 60, "M5": 300, "M15": 900, "M30": 1800, "H1": 3600, "H4": 14400, "D1": 86400, "W1": 604800, "MN1": 2592000}
# Segundos que una serie se considera al día dentro de su vela actual, y hasta cuándo se sirve vencida (refrescando aparte).
_TTL_TF = {"M1": 5.0, "M5": 10.0, "M15": 20.0, "M30": 30.0, "H1": 30.0, "H4": 60.0, "D1": 120.0, "W1": 300.0, "MN1": 600.0}
_FACTOR_VENCIDA = 6
# Velas que se piden al refrescar una serie ya guardada, y segundos mínimos entre dos lecturas de «la última vela».
_VELAS_REFRESCO = 12
_TTL_ULTIMA = 4.0
# Series: (símbolo, tf) -> {"t": instante de la última actualización, "velas": [...]}.
_SERIES: dict = {}
_CANDADOS: dict = {}
_CANDADO_TABLAS = threading.Lock()
_EN_REFRESCO: set = set()
_AGOTADAS: dict = {}     # (símbolo, tf) -> instante en que Capital no tenía velas más antiguas
# Hilos de fondo para precargar y refrescar (pocos: el backend ya limita el ritmo de peticiones).
_FONDO = ThreadPoolExecutor(max_workers=2, thread_name_prefix="velas-fondo")
# Temporalidad que se pidió por última vez (la que se precarga para los demás activos) y cuándo se precalentó cada activo.
_TF_RECIENTE = ["H1"]
_PRECALENTADO: dict = {}
_ESPERA_PRECALENTAR = 120.0


def _leer(simbolo: str, tf: str, n: int) -> list:
    """Lee `n` velas de MT5 y las convierte a la lista de dicts del gráfico (lista vacía si MT5 no entrega datos).

    Convierte por columnas, no fila por fila: con 5000 velas es mucho más rápido. Cada valor se redondea con `round`
    de Python, igual que antes. Inicializa MT5 y consulta el histórico (con CANDADO_MT5 si el proveedor es MT5)."""
    with CANDADO_MT5:
        inicializar_mt5()
        df = obtener_datos_historicos(simbolo, timeframe=TF_MAP.get(tf, mt5.TIMEFRAME_H1), n_velas=n)
    return _filas_a_velas(df)


def _filas_a_velas(df) -> list:
    """Convierte el DataFrame de velas (índice de tiempo, columnas open/high/low/close/tick_volume y, si existe, spread) a la lista de dicts del gráfico."""
    if df.empty:
        return []
    tiempos = [int(t.timestamp()) for t in df.index]
    abre = [round(x, 5) for x in df["open"].astype(float).tolist()]
    alto = [round(x, 5) for x in df["high"].astype(float).tolist()]
    bajo = [round(x, 5) for x in df["low"].astype(float).tolist()]
    cierra = [round(x, 5) for x in df["close"].astype(float).tolist()]
    volumen = df["tick_volume"].astype(float).tolist()
    spread = df["spread"].astype(float).tolist() if "spread" in df.columns else [0.0] * len(tiempos)   # puntos; lo usa el backtest
    return [{"time": t, "open": o, "high": h, "low": l, "close": c, "volume": v, "spread": sp}
            for t, o, h, l, c, v, sp in zip(tiempos, abre, alto, bajo, cierra, volumen, spread)]


def _leer_con_reintentos(simbolo: str, tf: str, n: int) -> list:
    """Lee `n` velas; si el proveedor devuelve vacío (el terminal descarga el historial) reintenta `_REINTENTOS` veces y,
    para peticiones grandes, prueba por último con 500 velas."""
    velas = _leer(simbolo, tf, n)
    intento = 1
    while not velas and intento < _REINTENTOS:
        time.sleep(_PAUSA)
        velas = _leer(simbolo, tf, n)
        intento += 1
    if not velas and n > 500:
        velas = _leer(simbolo, tf, 500)
    return velas


def _candado_de(clave):
    """Candado propio de cada (símbolo, tf): dos peticiones a la misma serie no la leen dos veces, la segunda espera a la primera."""
    with _CANDADO_TABLAS:
        return _CANDADOS.setdefault(clave, threading.Lock())


def _fusionar(guardadas: list, nuevas: list) -> list:
    """Une las velas guardadas con un tramo final más reciente: desde la primera vela nueva se reemplaza lo guardado."""
    if not nuevas:
        return guardadas
    corte = nuevas[0]["time"]
    return [v for v in guardadas if v["time"] < corte] + nuevas


def _guardar(clave, velas: list) -> None:
    """Guarda (o reemplaza) la serie de una clave con la hora actual."""
    with _CANDADO_TABLAS:
        _SERIES[clave] = {"t": time.time(), "velas": velas}


def _refrescar_serie(simbolo: str, tf: str, desde: float = 0.0) -> list:
    """Actualiza la serie guardada pidiendo solo las últimas velas y devuelve la serie completa (lista vacía si no hay datos).

    Si no había serie guardada, lee la serie larga completa. Toma el candado de la clave: si varias peticiones llegan a la vez,
    solo la primera lee; las demás, al obtener el candado, ven que la serie se actualizó después de que ellas llegaran
    (`desde` es el instante de su llegada) y la usan sin volver a leer."""
    clave = (simbolo, tf)
    with _candado_de(clave):
        reg = _SERIES.get(clave)
        if reg and desde and reg["t"] >= desde and reg["velas"]:
            return reg["velas"]
        if reg and len(reg["velas"]) >= 2:
            nuevas = _leer(simbolo, tf, _VELAS_REFRESCO)
            if nuevas:
                velas = _fusionar(reg["velas"], nuevas)
                _guardar(clave, velas)
                return velas
            return reg["velas"]
        velas = _leer_con_reintentos(simbolo, tf, _LARGO_SERIE)
        if velas:
            _guardar(clave, velas)
        return velas


def _limpio(simbolo: str) -> str:
    """Nombre del símbolo sin los puntos suspensivos con que la lista de activos abrevia algunos (`EURUSD...`): el feed los pide
    con ellos y el gráfico sin ellos, y la caché debe usar un solo nombre."""
    return simbolo.replace("...", "").replace("…", "").strip()


def _marcar_fondo() -> None:
    """Marca el hilo actual como de segundo plano para el limitador de peticiones de Capital.com (no hace nada con MT5)."""
    if _ES_CAPITAL:
        from herramientas.backends.capital import marcar_hilo_fondo
        marcar_hilo_fondo()


def _refrescar_en_fondo(simbolo: str, tf: str) -> None:
    """Pide a un hilo de fondo que actualice una serie, salvo que ya haya una actualización en curso de esa serie."""
    clave = (simbolo, tf)
    with _CANDADO_TABLAS:
        if clave in _EN_REFRESCO:
            return
        _EN_REFRESCO.add(clave)

    def _tarea():
        _marcar_fondo()
        try:
            _refrescar_serie(simbolo, tf)
        except Exception:
            pass
        finally:
            with _CANDADO_TABLAS:
                _EN_REFRESCO.discard(clave)
    _FONDO.submit(_tarea)


def _profundizar(simbolo: str, tf: str, n: int) -> list:
    """Amplía hacia atrás la serie guardada hasta `n` velas (máximo `_LARGO_MAX`) y devuelve la serie completa.

    Pide solo las velas anteriores a la primera guardada. Si Capital.com no tiene más, lo recuerda `_REINTENTO_AGOTADA` segundos
    para no repetir la consulta en cada petición. La temporalidad mensual no se amplía (se arma con velas semanales y diarias).
    Toma el candado de la serie; la hora de la última actualización no cambia, porque el tramo final no se ha vuelto a leer."""
    clave = (simbolo, tf)
    n = min(int(n), _LARGO_MAX)
    with _candado_de(clave):
        reg = _SERIES.get(clave)
        if not reg or not reg["velas"] or len(reg["velas"]) >= n or tf == "MN1":
            return reg["velas"] if reg else []
        if time.time() - _AGOTADAS.get(clave, 0.0) < _REINTENTO_AGOTADA:
            return reg["velas"]
        from herramientas.backends.capital import obtener_datos_anteriores
        df = obtener_datos_anteriores(simbolo, TF_MAP.get(tf, mt5.TIMEFRAME_H1), reg["velas"][0]["time"], n - len(reg["velas"]))
        antiguas = _filas_a_velas(df)
        if not antiguas:
            _AGOTADAS[clave] = time.time()
            return reg["velas"]
        if len(antiguas) < n - len(reg["velas"]):
            _AGOTADAS[clave] = time.time()      # llegó al comienzo del historial
        velas = [v for v in antiguas if v["time"] < reg["velas"][0]["time"]] + reg["velas"]
        with _CANDADO_TABLAS:
            reg["velas"] = velas
        return velas


def _profundizar_en_fondo(simbolo: str, tf: str, n: int) -> None:
    """Pide a un hilo de fondo que amplíe una serie hacia atrás, salvo que ya haya una ampliación en curso de esa serie."""
    clave = (simbolo, tf, "ampliar")
    with _CANDADO_TABLAS:
        if clave in _EN_REFRESCO:
            return
        _EN_REFRESCO.add(clave)

    def _tarea():
        _marcar_fondo()
        try:
            _profundizar(simbolo, tf, n)
        except Exception:
            pass
        finally:
            with _CANDADO_TABLAS:
                _EN_REFRESCO.discard(clave)
    _FONDO.submit(_tarea)


def _serie_capital(simbolo: str, tf: str, n: int) -> list:
    """Velas de Capital.com para (símbolo, tf), con la serie en memoria al día y ampliada hacia atrás si se piden más de las guardadas."""
    velas = _serie_al_dia(simbolo, tf, n)
    if velas and n > len(velas):
        if n <= _LARGO_GRAFICO:
            _profundizar_en_fondo(simbolo, tf, n)     # el gráfico no espera: recibe lo guardado y la próxima vez, la serie ampliada
        else:
            velas = _profundizar(simbolo, tf, n)      # backtest y replay necesitan todas las velas pedidas
    return velas


def _serie_al_dia(simbolo: str, tf: str, n: int) -> list:
    """Serie de (símbolo, tf) lista para usar: la guardada si sirve o la que resulta de refrescarla (ver el docstring del módulo)."""
    clave = (simbolo, tf)
    llegada = time.time()
    necesarias = min(n, _LARGO_SERIE)
    reg = _SERIES.get(clave)
    if reg and len(reg["velas"]) >= min(necesarias, 2):
        ahora = time.time()
        seg = _SEG_TF[tf]
        edad = ahora - reg["t"]
        misma_vela = int(reg["t"] // seg) == int(ahora // seg)
        ttl = _TTL_TF[tf]
        if misma_vela and edad < ttl:
            return reg["velas"]
        if misma_vela and edad < ttl * _FACTOR_VENCIDA:
            _refrescar_en_fondo(simbolo, tf)
            return reg["velas"]
    return _refrescar_serie(simbolo, tf, llegada)


def _precalentar_temporalidades(simbolo: str, tf_actual: str) -> None:
    """Precarga en segundo plano las demás temporalidades de un activo (las más cercanas a la actual primero)."""
    ahora = time.time()
    with _CANDADO_TABLAS:
        if ahora - _PRECALENTADO.get(("tf", simbolo), 0.0) < _ESPERA_PRECALENTAR:
            return
        _PRECALENTADO[("tf", simbolo)] = ahora
    orden = list(_SEG_TF)
    pos = orden.index(tf_actual)
    for otro in sorted((t for t in orden if t != tf_actual), key=lambda t: abs(orden.index(t) - pos)):
        if (simbolo, otro) not in _SERIES:
            _FONDO.submit(_serie_silenciosa, simbolo, otro)


def _serie_silenciosa(simbolo: str, tf: str) -> None:
    """Carga una serie en segundo plano ignorando cualquier error (es solo una precarga)."""
    _marcar_fondo()
    try:
        _refrescar_serie(simbolo, tf)
    except Exception:
        pass


def precalentar(simbolos) -> None:
    """Precarga en segundo plano la temporalidad en uso de cada activo de la lista, para que cambiar de activo sea instantáneo.

    Recibe los símbolos que pidió el feed. Solo actúa con Capital.com, como mucho una vez cada `_ESPERA_PRECALENTAR`
    segundos por activo y para los primeros 12; no espera a que terminen las lecturas."""
    if not _ES_CAPITAL:
        return
    tf = _TF_RECIENTE[0]
    ahora = time.time()
    for simbolo in list(dict.fromkeys(_limpio(x) for x in simbolos))[:12]:
        with _CANDADO_TABLAS:
            if ahora - _PRECALENTADO.get((tf, simbolo), 0.0) < _ESPERA_PRECALENTAR:
                continue
            _PRECALENTADO[(tf, simbolo)] = ahora
        if (simbolo, tf) not in _SERIES:
            _FONDO.submit(_serie_silenciosa, simbolo, tf)


def obtener_ultima(simbolo: str, tf: str) -> dict:
    """Última vela de (símbolo, tf), o {} si no hay datos. Con Capital.com se resuelve de la serie guardada y solo se vuelve a
    leer cada `_TTL_ULTIMA` segundos, aunque el gráfico la consulte cada 1,5 s; con MT5 se lee siempre del terminal."""
    if _ES_CAPITAL and tf in _SEG_TF:
        simbolo = _limpio(simbolo)
        reg = _SERIES.get((simbolo, tf))
        if reg and time.time() - reg["t"] < _TTL_ULTIMA and reg["velas"]:
            return reg["velas"][-1]
        velas = _refrescar_serie(simbolo, tf, time.time())
        return velas[-1] if velas else {}
    velas = obtener_velas(simbolo, tf, 2)
    return velas[-1] if velas else {}


def obtener_velas(simbolo: str, tf: str, n: int) -> list:
    """Devuelve una lista de velas OHLC en formato JSON para Lightweight Charts.

    Recibe el símbolo, la temporalidad como texto (clave de TF_MAP; si no existe se usa H1)
    y la cantidad `n` de velas. Cada vela es un dict con time (segundos UNIX), open, high,
    low, close (redondeados a 5 decimales), volume (tick_volume) y spread (puntos, 0.0 si
    el dato no existe). Devuelve una lista vacía si el proveedor no entrega datos.
    Con Capital.com se usa la serie en memoria (ver el docstring del módulo) y se precargan las demás temporalidades del
    activo. Con MT5, las peticiones de `_N_MIN_CACHE` velas o más se sirven de memoria durante `_TTL_CACHE` segundos; si MT5 devuelve
    vacío se reintenta `_REINTENTOS` veces y, para peticiones grandes, se prueba por último con 500 velas.
    """
    if _ES_CAPITAL and tf in _SEG_TF:
        simbolo = _limpio(simbolo)
        _TF_RECIENTE[0] = tf
        velas = _serie_capital(simbolo, tf, n)
        _precalentar_temporalidades(simbolo, tf)
        return velas[-n:] if 0 < n < len(velas) else velas
    grande = n >= _N_MIN_CACHE
    clave = (simbolo, tf, n)
    if grande:
        guardada = _CACHE.get(clave)
        if guardada and time.monotonic() - guardada[0] < _TTL_CACHE:
            return guardada[1]
    velas = _leer_con_reintentos(simbolo, tf, n)
    if grande and velas:
        if len(_CACHE) >= _MAX_CACHE:
            _CACHE.pop(min(_CACHE, key=lambda k: _CACHE[k][0]), None)
        _CACHE[clave] = (time.monotonic(), velas)
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
