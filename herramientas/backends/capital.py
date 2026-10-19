# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ------------------------------------ INICIO Piña y Jara capital .PY -----------------------------------
# -------------------------------------------------------------------------------------------------------

"""
capital.py  —  Backend de Capital.com (API REST)  —  16-10-2026
---------------------------------------------------------------
Implementa el MISMO contrato público que `herramientas/puente_mt5.py`, pero hablando
con Capital.com por HTTPS en vez de con el terminal MetaTrader 5. Así la plataforma
funciona SIN terminal ni Windows: basta poner PROVEEDOR=capital en el .env.

Los nombres de funciones se mantienen idénticos a los del puente MT5 (incluido
`inicializar_mt5` y `MT5_LOCK`) para que sea un reemplazo directo: los ~45 archivos
que hacen `from herramientas.puente_mt5 import ...` no cambian.

CREDENCIALES (.env):
    CAPITAL_API_KEY       clave API generada en Capital.com
    CAPITAL_IDENTIFIER    correo de la cuenta
    CAPITAL_API_PASSWORD  contraseña de la KEY (la que define/genera la propia key)
    CAPITAL_DEMO          true | false

DIFERENCIAS con MT5 (documentadas donde aplican):
  - Los "ticket" de MT5 (enteros) son aquí "dealId" (texto).
  - El "volumen/lotes" de MT5 es aquí "size".
  - No hay profundidad de mercado (DOM) por REST -> `obtener_dom` responde no disponible.
  - La sesión caduca a los 10 min: se renueva automáticamente.
  - No hay campo "swap" por posición -> se informa 0.0 (el P/G usa `upl`).
"""

import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone

import certifi
import pandas as pd  # type: ignore[import-untyped]
import requests
from dotenv import load_dotenv

# --- SSL para la ruta con tildes del proyecto (mismo fix que yfinance) ---
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

load_dotenv()

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
_ES_DEMO = os.getenv("CAPITAL_DEMO", "true").strip().lower() in ("true", "1", "si", "sí")
BASE = ("https://demo-api-capital.backend-capital.com/api/v1" if _ES_DEMO
        else "https://api-capital.backend-capital.com/api/v1")
_API_KEY = os.getenv("CAPITAL_API_KEY", "").strip()
_IDENTIFIER = os.getenv("CAPITAL_IDENTIFIER", "").strip()
_API_CONTRASENA = os.getenv("CAPITAL_API_PASSWORD", "").strip()

# Candado de acceso: mantiene el mismo nombre que usaba el puente MT5, porque
# muchos módulos hacen `with MT5_LOCK:` al leer/operar. Aquí serializa el refresco
# de la sesión y las llamadas sensibles.
MT5_LOCK = threading.RLock()
_ORDEN_CANDADO = MT5_LOCK

# Caché de lecturas (cuenta, precio, posiciones): como cada llamada REST a Capital
# tarda ~300-500 ms y el dashboard re-ejecuta toda la página en cada interacción,
# se cachean unos segundos. El precio/P-G EN VIVO llega por SSE/WebSocket, así que
# un desfase de pocos segundos en estas lecturas no se nota.
_cache_lectura: dict = {}          # clave -> (ts, valor)
_TIEMPO_VIDA_CUENTA = 2.0
_TIEMPO_VIDA_PRECIO = 3.0
_TIEMPO_VIDA_POSICIONES = 2.0
_STALE_MAX = 120.0                 # una lectura vencida se sirve al instante (y se refresca aparte) hasta esta edad
_refrescando: set = set()
_tl = threading.local()


# TITULO CACHE CON REFRESCO

def _cache_con_refresco(clave, tiempo_vida, funcion, *args):
    """Caché "stale-while-revalidate": devuelve el valor vigente; si venció (pero es reciente) lo devuelve
    igual AL INSTANTE y lo refresca en un hilo aparte, para que ningún rerun de la página espere ~300 ms
    por cada llamada REST (los valores en vivo ya llegan por el WebSocket). None = no hay caché utilizable."""
    impacto = _cache_lectura.get(clave)
    if not impacto or getattr(_tl, "bg", False):
        return None
    edad = time.time() - impacto[0]
    if edad < tiempo_vida:
        return impacto[1]
    if edad < _STALE_MAX:
        if clave not in _refrescando:
            _refrescando.add(clave)

            def _run():
                """Hilo de refresco: vuelve a calcular el valor vencido sin bloquear a quien lo pidió y lo deja en la caché."""
                _tl.bg = True
                try:
                    funcion(*args)
                except Exception:
                    pass
                finally:
                    _refrescando.discard(clave)
            threading.Thread(target=_run, daemon=True).start()
        return impacto[1]
    return None


# TITULO OBTENER MERCADO

def obtener_mercado(epic: str) -> dict:
    """GET /markets/{epic} (JSON crudo) con caché 30 s + refresco en segundo plano. {} si falla.
    Lo comparten especs_posicion y el shim (symbol_info): una sola llamada por instrumento."""
    clave = f"mercado:{epic}"
    v = _cache_con_refresco(clave, 30.0, obtener_mercado, epic)
    if v is not None:
        return v
    r = _pedir("GET", f"/markets/{epic}")
    for _ in range(2):        # fallo transitorio (p. ej. límite de peticiones con muchas en paralelo): reintenta
        if r is not None and (r.status_code == 200 or r.status_code == 404):
            break
        time.sleep(0.5)
        r = _pedir("GET", f"/markets/{epic}")
    data = r.json() if (r is not None and r.status_code == 200) else {}
    if data:
        _cache_lectura[clave] = (time.time(), data)
    return data


# TITULO LEER JSON

def leer_json(ruta: str, tiempo_vida: float = 2.0, parametros: dict = None):
    """GET `ruta` y devuelve el JSON (o None si falla), con caché corta + refresco en segundo plano.
    Para lecturas repetidas en cada rerun de la página (/positions, /workingorders, /history/...)."""
    clave = f"raw:{ruta}:{sorted((parametros or {}).items())}"
    v = _cache_con_refresco(clave, tiempo_vida, leer_json, ruta, tiempo_vida, parametros)
    if v is not None:
        return v
    r = _pedir("GET", ruta, parametros=parametros)
    if r is None or r.status_code != 200:
        return None
    data = r.json()
    _cache_lectura[clave] = (time.time(), data)
    return data


# TITULO INVALIDAR

def _invalidar() -> None:
    """Tras operar (abrir/cerrar/modificar) se descartan las lecturas para no servir datos viejos."""
    for k in list(_cache_lectura):
        if k in ("posiciones", "cuenta") or k.startswith(("raw:/positions", "raw:/workingorders", "raw:/history")):
            _cache_lectura.pop(k, None)

# Estado de sesión (tokens de Capital.com)
_HTTP = requests.Session()
_tokens: dict = {"CST": "", "X-SECURITY-TOKEN": ""}
_ultimo_uso = 0.0            # epoch del último uso con éxito (para renovar antes de 10 min)
_VIDA_TOKEN_S = 540          # renovar la sesión si pasaron >9 min
_cuenta_activa_id = ""
_CANDADO_SESION = threading.RLock()   # solo serializa la apertura/renovación de la sesión

_TIEMPO_ESPERA = 15


# TITULO ABRIR SESION

# ---------------------------------------------------------------------------
# Sesión y peticiones
# ---------------------------------------------------------------------------
def _abrir_sesion() -> bool:
    """POST /session -> guarda CST y X-SECURITY-TOKEN. Devuelve True si conecta."""
    global _ultimo_uso, _cuenta_activa_id
    if not (_API_KEY and _IDENTIFIER and _API_CONTRASENA):
        print("[CAPITAL] Faltan credenciales en el .env "
              "(CAPITAL_API_KEY / CAPITAL_IDENTIFIER / CAPITAL_API_PASSWORD).")
        return False
    try:
        r = _HTTP.post(
            f"{BASE}/session",
            headers={"X-CAP-API-KEY": _API_KEY, "Content-Type": "application/json"},
            json={"identifier": _IDENTIFIER, "password": _API_CONTRASENA,
                  "encryptedPassword": False},
            timeout=_TIEMPO_ESPERA,
        )
    except requests.exceptions.RequestException as e:
        print(f"[CAPITAL] No se pudo contactar a Capital.com: {e}")
        return False
    if r.status_code != 200:
        print(f"[CAPITAL] Falló la sesión (HTTP {r.status_code}): {r.text}")
        return False
    _tokens["CST"] = r.headers.get("CST", "")
    _tokens["X-SECURITY-TOKEN"] = r.headers.get("X-SECURITY-TOKEN", "")
    try:
        _cuenta_activa_id = r.json().get("accountId", "")
    except Exception:
        _cuenta_activa_id = ""
    _ultimo_uso = time.time()
    return bool(_tokens["CST"] and _tokens["X-SECURITY-TOKEN"])


# TITULO INICIALIZAR MT5

def inicializar_mt5(inicio_sesion=None, contrasena=None, servidor=None) -> bool:
    """Compat: asegura una sesión activa con Capital.com (nombre heredado del puente).

    Los parámetros login/password/server se ignoran (eran de MT5); las credenciales
    salen del .env. Renueva la sesión si está por caducar."""
    # Vía rápida SIN candado: con sesión vigente las lecturas no se esperan entre sí.
    if _tokens["CST"] and (time.time() - _ultimo_uso) < _VIDA_TOKEN_S:
        return True
    with _CANDADO_SESION:
        if _tokens["CST"] and (time.time() - _ultimo_uso) < _VIDA_TOKEN_S:
            return True
        return _abrir_sesion()


# TITULO CERRAR MT5

def cerrar_mt5():
    """Compat: cierra la sesión con Capital.com."""
    with MT5_LOCK:
        try:
            if _tokens["CST"]:
                _HTTP.delete(f"{BASE}/session", headers=_cabeceras(), timeout=_TIEMPO_ESPERA)
        except Exception:
            pass
        _tokens["CST"] = _tokens["X-SECURITY-TOKEN"] = ""


# TITULO CABECERAS

def _cabeceras() -> dict:
    """Devuelve las cabeceras de autenticación (CST y X-SECURITY-TOKEN) de la sesión activa."""
    return {"CST": _tokens["CST"], "X-SECURITY-TOKEN": _tokens["X-SECURITY-TOKEN"]}


# TITULO PEDIR

def _pedir(metodo: str, ruta: str, *, parametros=None, json=None, reintento=True):
    """Petición autenticada. Renueva sesión si hace falta y reintenta una vez ante 401.
    Devuelve el objeto requests.Response, o None si no hay conexión."""
    # Sin candado global durante la petición: antes cada llamada (~300-800 ms) bloqueaba a todas las
    # demás, y los refrescos en segundo plano retrasaban al rerun de la página. Solo la apertura de
    # sesión se serializa (en inicializar_mt5).
    if not inicializar_mt5():
        return None
    try:
        r = _HTTP.request(metodo, f"{BASE}{ruta}", headers=_cabeceras(),
                          params=parametros, json=json, timeout=_TIEMPO_ESPERA)
    except requests.exceptions.RequestException as e:
        print(f"[CAPITAL] Error de red en {metodo} {ruta}: {e}")
        return None
    # Token caducado/ inválido -> reautenticar una vez
    if r.status_code == 401 and reintento:
        with _CANDADO_SESION:
            _tokens["CST"] = ""
            correcto = _abrir_sesion()
        if correcto:
            return _pedir(metodo, ruta, parametros=parametros, json=json, reintento=False)
    if r.status_code < 400:
        global _ultimo_uso
        _ultimo_uso = time.time()
    return r


# ---------------------------------------------------------------------------
# Resolución de símbolos (nombre del proyecto -> epic de Capital.com)
# ---------------------------------------------------------------------------
# Capital nombra los instrumentos con un "epic". Varios ya coinciden con los alias
# del proyecto (GOLD, US30, US100...). Mapeamos el núcleo del símbolo al epic.
_ALIAS_EPIC = {
    "XAUUSD": "GOLD", "GOLD": "GOLD",
    "XAGUSD": "SILVER", "SILVER": "SILVER",
    "US30": "US30", "US30CASH": "US30", "DJ30": "US30", "WS30": "US30", "DOWJONES": "US30",
    "NAS100": "US100", "US100": "US100", "US100CASH": "US100", "USTEC": "US100", "NDX100": "US100",
    "US500": "US500", "SPX500": "US500", "US500CASH": "US500", "SP500": "US500",
    "BTCUSD": "BTCUSD", "ETHUSD": "ETHUSD", "XRPUSD": "XRPUSD",
    # Índices: nombres típicos de MT5/XM -> epic de Capital (sin esto la búsqueda por texto devolvía otro
    # instrumento, p. ej. ESP35 -> un ETF y US2000/AUS200 -> US100)
    "US2000": "RTY", "RUSSELL2000": "RTY", "RUT": "RTY", "VIX": "VIX", "DXY": "DXY", "USDX": "DXY",
    "GER40": "DE40", "DE40": "DE40", "DAX40": "DE40", "UK100": "UK100", "FTSE100": "UK100",
    "FRA40": "FR40", "FR40": "FR40", "CAC40": "FR40", "ESP35": "SP35", "SPAIN": "SP35", "SPAIN35": "SP35",
    "SP35": "SP35", "IBEX35": "SP35", "EU50": "EU50", "STOXX50": "EU50", "ITA40": "IT40", "IT40": "IT40",
    "NETH25": "NL25", "NL25": "NL25", "AEX25": "NL25", "SWI20": "SW20", "SW20": "SW20",
    "JP225": "J225", "J225": "J225", "NIKKEI225": "J225", "AUS200": "AU200", "AU200": "AU200",
    "HK50": "HK50", "HSI": "HK50", "CHINA50": "CN50", "CHN50": "CN50", "CN50": "CN50",
    # Materias primas
    "XPTUSD": "PLATINUM", "XPDUSD": "PALLADIUM", "XCUUSD": "COPPER", "HGCOP": "COPPER", "COPPER": "COPPER",
    "USOIL": "OIL_CRUDE", "WTI": "OIL_CRUDE", "UKOIL": "OIL_BRENT", "BRENT": "OIL_BRENT",
    "NGAS": "NATURALGAS", "NATGAS": "NATURALGAS", "COFFEE": "COFFEEARABICA", "COCOA": "USCOCOA",
    "SUGAR": "SB", "WHEAT": "WHEAT", "CORN": "CORN", "SOYBEAN": "SOYBEAN", "COTTON": "USCOTTON",
}
_cache_epic: dict = {}


# TITULO CORE SIMBOLO

def _core_simbolo(name: str) -> str:
    """Núcleo comparable de un símbolo: sin '...' ni sufijos de bróker."""
    s = (name or "").upper().strip().replace("...", "").strip("#")
    if s.endswith("MICRO"):
        s = s[:-5]
    if "." in s:
        base, sufijo = s.rsplit(".", 1)
        if sufijo.isalnum() and 1 <= len(sufijo) <= 4:
            s = base
    return s


# TITULO BUSCAR EPIC

def _buscar_epic(termino: str):
    """Busca el epic de Capital por texto (GET /markets?searchTerm). Prefiere coincidencia
    exacta de epic; si no, el primer resultado. None si no hay nada."""
    if not termino:
        return None
    try:
        r = _pedir("GET", "/markets", parametros={"searchTerm": termino})
        if r is not None and r.status_code == 200:
            mercados = r.json().get("markets", [])
            for m in mercados:
                if str(m.get("epic", "")).upper() == termino.upper():
                    return m["epic"]
            if mercados:
                return mercados[0].get("epic")
    except Exception:
        pass
    return None


_RUTA_EPICS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                           "data", "epics_resueltos.json")
_RUTA_CATALOGO = os.path.join(os.path.dirname(_RUTA_EPICS), "catalogo_capital.json")
_TIEMPO_VIDA_FALLO_EPIC = 3 * 86400        # un símbolo sin epic se vuelve a buscar recién a los 3 días
_CANDADO_EPICS = threading.Lock()
_epics_disco: dict = {}            # símbolo -> {"e": epic, "ok": bool, "t": epoch}
_epics_catalogo: set = set()


# TITULO CARGAR EPICS

def _cargar_epics() -> None:
    """Carga de disco los epics ya resueltos (evita cientos de búsquedas REST al reiniciar) y los nombres del catálogo."""
    try:
        with open(_RUTA_EPICS, "r", encoding="utf-8") as f:
            _epics_disco.update(json.load(f))
    except Exception:
        pass
    try:
        with open(_RUTA_CATALOGO, "r", encoding="utf-8") as f:
            _epics_catalogo.update(str(x.get("name", "")).upper() for x in json.load(f))
    except Exception:
        pass


# TITULO GUARDAR EPICS

def _guardar_epics() -> None:
    """Guarda en disco, de forma atómica, los epics ya resueltos (`data/epics_resueltos.json`). Ignora los errores de escritura."""
    try:
        os.makedirs(os.path.dirname(_RUTA_EPICS), exist_ok=True)
        tmp = _RUTA_EPICS + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_epics_disco, f)
        os.replace(tmp, _RUTA_EPICS)
    except Exception:
        pass


# TITULO RESOLVER SIMBOLO

def resolver_simbolo(symbol: str) -> str:
    """Epic de Capital.com para un símbolo del proyecto: alias → catálogo/disco → ¿el núcleo es un epic? →
    búsqueda por texto. Los resultados (y los fallos, 3 días) se guardan en disco: tras el primer uso, resolver
    un símbolo ya conocido no hace ninguna llamada REST."""
    if not symbol:
        return symbol
    if symbol in _cache_epic:
        return _cache_epic[symbol]
    core = _core_simbolo(symbol)
    epic = _ALIAS_EPIC.get(core)
    if epic is not None:                      # los alias mandan sobre lo guardado en disco
        _cache_epic[symbol] = epic
        return epic
    d = _epics_disco.get(symbol)
    if d and (d.get("ok") or time.time() - float(d.get("t", 0)) < _TIEMPO_VIDA_FALLO_EPIC):
        _cache_epic[symbol] = d["e"]
        return d["e"]
    correcto = True
    if epic is None:
        if core in _epics_catalogo:
            epic = core                       # está en el catálogo local: sin llamada REST
        else:
            # ¿el núcleo ya es un epic válido? Si tiene precio, úsalo; si no, búscalo por texto.
            r = _pedir("GET", f"/markets/{core}")
            if r is not None and r.status_code == 200:
                epic = core
            else:
                epic = _buscar_epic(core) or _buscar_epic(symbol)
                correcto = epic is not None
                epic = epic or core
    _cache_epic[symbol] = epic
    with _CANDADO_EPICS:
        _epics_disco[symbol] = {"e": epic, "ok": correcto, "t": time.time()}
        _guardar_epics()
    return epic


_cargar_epics()

_RUTA_VALIDOS = os.path.join(os.path.dirname(_RUTA_EPICS), "epics_validos.json")
_validos: set = set()


# TITULO EPIC EXISTE

def epic_existe(epic: str) -> bool:
    """¿Existe este epic en Capital? Los que ya se comprobaron una vez se recuerdan en disco (no cambian), así
    la vista Cotizaciones no repite ~50 consultas en cada arranque."""
    if not epic:
        return False
    if not _validos:
        try:
            with open(_RUTA_VALIDOS, "r", encoding="utf-8") as f:
                _validos.update(json.load(f))
        except Exception:
            _validos.add("")          # marca "ya intenté leer" aunque el archivo no exista
    if epic in _validos:
        return True
    if obtener_mercado(epic):
        _validos.add(epic)
        try:
            tmp = _RUTA_VALIDOS + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(sorted(_validos - {""}), f)
            os.replace(tmp, _RUTA_VALIDOS)
        except Exception:
            pass
        return True
    return False


# ---------------------------------------------------------------------------
# Timeframes:  constante MT5 (int) o texto -> resolución de Capital.com
# ---------------------------------------------------------------------------
# Valores enteros de MetaTrader5.TIMEFRAME_* (para no importar el paquete MT5).
_TEMPORALIDAD_MT5_A_CAPITAL = {
    1: "MINUTE", 5: "MINUTE_5", 15: "MINUTE_15", 30: "MINUTE_30",
    16385: "HOUR", 16388: "HOUR_4", 16408: "DAY", 32769: "WEEK",
}
_RESOLUCIONES = {"MINUTE", "MINUTE_5", "MINUTE_15", "MINUTE_30", "HOUR", "HOUR_4", "DAY", "WEEK"}
TIMEFRAME_H1 = 16385   # por si algún caller usa backends.capital.TIMEFRAME_H1


# TITULO RESOLUCION

def _resolucion(timeframe) -> str:
    """Traduce una temporalidad de MT5 (constante numérica) a la resolución de Capital ("MINUTE", "HOUR", "DAY"…)."""
    if isinstance(timeframe, str) and timeframe.upper() in _RESOLUCIONES:
        return timeframe.upper()
    return _TEMPORALIDAD_MT5_A_CAPITAL.get(int(timeframe) if timeframe is not None else 16385, "HOUR")


# TITULO SEG RESOLUCION

def _segundos_resolucion(resolucion: str) -> int:
    """Devuelve cuántos segundos dura una vela de la resolución de Capital indicada."""
    return {"MINUTE": 60, "MINUTE_5": 300, "MINUTE_15": 900, "MINUTE_30": 1800,
            "HOUR": 3600, "HOUR_4": 14400, "DAY": 86400, "WEEK": 604800}.get(resolucion, 3600)


# TITULO EPOCH UTC

def _epoch_utc(texto: str) -> int:
    """Convierte 'YYYY-MM-DDTHH:MM:SS(.mmm)' (UTC) a epoch en segundos."""
    if not texto:
        return 0
    t = texto.replace("Z", "")
    for formato in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return int(datetime.strptime(t, formato).replace(tzinfo=timezone.utc).timestamp())
        except ValueError:
            continue
    return 0


# TITULO CUENTA PREFERIDA

# ---------------------------------------------------------------------------
# Cuenta
# ---------------------------------------------------------------------------
def _cuenta_preferida() -> dict:
    """Devuelve los datos de la cuenta marcada como preferida en Capital (balance, depósito, P/G y disponible), o un diccionario vacío si no hay conexión."""
    r = _pedir("GET", "/accounts")
    if r is None or r.status_code != 200:
        return {}
    cuentas = r.json().get("accounts", [])
    for c in cuentas:
        if c.get("preferred"):
            return c
    return cuentas[0] if cuentas else {}


_UNID_POR_LOTE_FX = 100000.0
_tipo_cache: dict = {}


# TITULO FACTOR LOTE

def factor_lote(tipo: str) -> float:
    """Unidades de Capital por 1 lote en la interfaz: el Forex (CURRENCIES) usa el lote estándar
    de 100.000 unidades; el resto de instrumentos usa 1 unidad = 1 lote (como hasta ahora)."""
    return _UNID_POR_LOTE_FX if str(tipo).upper() == "CURRENCIES" else 1.0


# TITULO FACTOR LOTE EPIC

def factor_lote_epic(epic: str) -> float:
    """Igual que factor_lote pero consultando el tipo del instrumento (cacheado)."""
    if epic not in _tipo_cache:
        r = _pedir("GET", f"/markets/{epic}")
        if r is not None and r.status_code == 200:
            _tipo_cache[epic] = (r.json().get("instrument", {}) or {}).get("type", "")
        else:
            return 1.0
    return factor_lote(_tipo_cache[epic])


# TITULO OBTENER INFO CUENTA

def obtener_info_cuenta() -> dict:
    """Balance, equity y margen de la cuenta activa (equivalente a MT5). Cacheado ~2 s."""
    _ahora = time.time()
    _v = _cache_con_refresco("cuenta", _TIEMPO_VIDA_CUENTA, obtener_info_cuenta)
    if _v is not None:
        return _v
    c = _cuenta_preferida()
    if not c:
        return {"error": "Sin conexión con Capital.com"}
    bal = c.get("balance", {}) or {}
    # Capital: `balance` YA incluye el P/G abierto (= equity); `deposit` es el saldo en efectivo.
    # Comprobado con la cuenta demo: margen = balance - available coincide con el margen real.
    equity = float(bal.get("balance", 0.0) or 0.0)
    balance = float(bal.get("deposit", 0.0) or 0.0) or (equity - float(bal.get("profitLoss", 0.0) or 0.0))
    ganancia_perdida = float(bal.get("profitLoss", 0.0) or 0.0)          # P/G de posiciones abiertas
    disponible = float(bal.get("available", 0.0) or 0.0)
    _resultado = {
        "login": c.get("accountId", ""),
        "nombre": c.get("accountName", ""),
        "servidor": "Capital.com (demo)" if _ES_DEMO else "Capital.com",
        "tipo": "Demo" if _ES_DEMO else "Real",
        "balance": balance,
        "equity": equity,
        "profit": ganancia_perdida,
        "margin": max(0.0, equity - disponible),
        "margin_free": disponible,
        "margin_level": (100.0 * equity / (equity - disponible))
                        if (equity - disponible) > 0 else 0.0,
        "credit": 0.0,
        "leverage": 0,
        "currency": c.get("currency", "USD"),
        "deposito": float(bal.get("deposit", 0.0) or 0.0),   # depósito de la cuenta (Capital /accounts)
    }
    _cache_lectura["cuenta"] = (_ahora, _resultado)
    return _resultado


# TITULO OBTENER POSICIONES

# ---------------------------------------------------------------------------
# Posiciones
# ---------------------------------------------------------------------------
def obtener_posiciones() -> list:
    """Posiciones abiertas (para la 'Cartera'). Cacheado ~2 s."""
    _ahora = time.time()
    _v = _cache_con_refresco("posiciones", _TIEMPO_VIDA_POSICIONES, obtener_posiciones)
    if _v is not None:
        return _v
    r = _pedir("GET", "/positions")
    if r is None or r.status_code != 200:
        return []
    salida = []
    for elemento in r.json().get("positions", []):
        p = elemento.get("position", {}) or {}
        m = elemento.get("market", {}) or {}
        es_compra = (p.get("direction", "").upper() == "BUY")
        # Al valorar: una COMPRA se cierra al bid; una VENTA al offer.
        actual = float(m.get("bid", 0.0) or 0.0) if es_compra else float(m.get("offer", 0.0) or 0.0)
        salida.append({
            "ticket": p.get("dealId", ""),            # dealId (texto), no int
            "symbol": m.get("epic", ""),
            "tipo": "Compra" if es_compra else "Venta",
            "volumen": float(p.get("size", 0.0) or 0.0) / factor_lote(m.get("instrumentType", "")),
            "precio_apertura": float(p.get("level", 0.0) or 0.0),
            "precio_actual": actual,
            "profit": float(p.get("upl", 0.0) or 0.0),   # P/G no realizado
            "swap": 0.0,                                 # Capital no lo da por posición
            "sl": float(p.get("stopLevel", 0.0) or 0.0),
            "tp": float(p.get("profitLevel", 0.0) or 0.0),
            "tiempo": _epoch_utc(p.get("createdDateUTC", "") or p.get("createdDate", "")),
        })
    _cache_lectura["posiciones"] = (_ahora, salida)
    return salida


# TITULO BUSCAR POSICION

def _buscar_posicion(dealId) -> dict:
    """Devuelve el item {position, market} de una posición por su dealId."""
    r = _pedir("GET", f"/positions/{dealId}")
    if r is not None and r.status_code == 200:
        return r.json()
    # Respaldo: recorrer todas
    r = _pedir("GET", "/positions")
    if r is None or r.status_code != 200:
        return {}
    for elemento in r.json().get("positions", []):
        if str(elemento.get("position", {}).get("dealId")) == str(dealId):
            return elemento
    return {}


# TITULO ESPECS POSICION

def especs_posicion(ticket) -> dict:
    """Datos del contrato de una posición para el panel de TP/SL de la Cartera.
    NOTA: `k` (valor por unidad de precio) es aproximado = contractSize, asumiendo
    instrumento cotizado en la moneda de la cuenta (USD). Afinar si se opera un
    instrumento con otra divisa de cotización."""
    elemento = _buscar_posicion(ticket)
    if not elemento:
        return {}
    p = elemento.get("position", {}) or {}
    epic = elemento.get("market", {}).get("epic", "")
    d = obtener_mercado(epic)
    if not d:
        return {}
    snap = d.get("snapshot", {}) or {}
    reglas = d.get("dealingRules", {}) or {}
    digitos = int(snap.get("decimalPlacesFactor", 2) or 2)
    punto = 10 ** (-digitos)
    bid = float(snap.get("bid", 0.0) or 0.0)
    ask = float(snap.get("offer", 0.0) or 0.0)
    contract = float(p.get("contractSize", 1.0) or 1.0)
    snap_tipo = (d.get("instrument", {}) or {}).get("type", "")
    # Distancia mínima de stop: Capital la da en % -> la pasamos a "puntos".
    md = reglas.get("minStopOrProfitDistance", {}) or {}
    if (md.get("unit") == "PERCENTAGE") and bid:
        distancia_precio = bid * float(md.get("value", 0.0) or 0.0) / 100.0
        stops_level = int(distancia_precio / punto) if punto else 0
    else:
        stops_level = int(float(md.get("value", 0.0) or 0.0) / punto) if punto else 0
    return {
        "k": contract * factor_lote(snap_tipo),
        "digitos": digitos,
        "point": float(punto),
        "stops_level": stops_level,
        "bid": bid,
        "ask": ask,
        "srv_now": float(time.time()),
        "precio_apertura": float(p.get("level", 0.0) or 0.0),
        "tipo": "Compra" if p.get("direction", "").upper() == "BUY" else "Venta",
        "volumen": float(p.get("size", 0.0) or 0.0) / factor_lote(snap_tipo),
    }


# TITULO OBTENER HISTORIAL

# ---------------------------------------------------------------------------
# Historial (operaciones cerradas)
# ---------------------------------------------------------------------------
def obtener_historial(dias: int = 90, limite: int = 100) -> list:
    """Operaciones cerradas (para el historial de Inicio).
    Lee /history/transactions del período y toma las de tipo negociación.
    NOTA: el nombre/forma exactos del P/G realizado se validan con una operación
    cerrada real; aquí se leen varios campos candidatos de forma defensiva."""
    # `from` al inicio del día: así la clave de caché no cambia cada segundo.
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%dT00:00:00")
    datos = leer_json("/history/transactions", 15.0, {"from": desde})
    if datos is None:
        return []
    salida = []
    for t in datos.get("transactions", []):
        tipo_transaccion = str(t.get("transactionType", "")).upper()
        if "TRADE" not in tipo_transaccion and "DEAL" not in tipo_transaccion:
            continue
        # P/G realizado: campos posibles según versión de la API.
        ganancia_perdida = (t.get("profitAndLoss") or t.get("pnl") or t.get("size") or 0)
        try:
            ganancia_perdida = float(str(ganancia_perdida).replace(t.get("currency", "") or "", "").strip() or 0)
        except ValueError:
            ganancia_perdida = 0.0
        salida.append({
            "ticket": t.get("reference", ""),
            "deal_id": t.get("dealId", ""),          # id de la posición (para detalle_cierre)
            "symbol": t.get("instrumentName", ""),
            "tipo": t.get("transactionType", ""),
            "volumen": 0.0,
            "precio_cierre": 0.0,
            "pg": ganancia_perdida,
            "fecha": _epoch_utc(t.get("dateUtc", "") or t.get("date", "")),
        })
    salida.sort(key=lambda x: x["fecha"], reverse=True)
    return salida[:limite]


# ---------------------------------------------------------------------------
# Detalle de una operación cerrada (para el Diario)
# ---------------------------------------------------------------------------
# /history/transactions solo da símbolo, P/L y fecha. El detalle (tamaño, dirección, precio de entrada y de
# salida, hora de apertura) sale de /history/activity, que solo admite ventanas de 24 h, filtrando por el
# dealId de la posición. Una operación cerrada no cambia: el resultado se guarda en disco.
_RUTA_CIERRES = os.path.join(os.path.dirname(_RUTA_EPICS), "cierres_capital.json")
_cierres: dict = {}
_CANDADO_CIERRES = threading.Lock()


# TITULO CARGAR CIERRES

def _cargar_cierres() -> None:
    """Carga de disco el detalle de las operaciones cerradas ya consultadas (`data/cierres_capital.json`). Ignora los errores de lectura."""
    try:
        with open(_RUTA_CIERRES, "r", encoding="utf-8") as f:
            _cierres.update(json.load(f))
    except Exception:
        pass


# TITULO ACTIVIDAD

def _actividad(deal_id: str, desde_marca_tiempo: float, hasta_marca_tiempo: float) -> list:
    """Actividades de una posición dentro de una ventana (máx. 24 h) en epoch UTC."""
    formato = "%Y-%m-%dT%H:%M:%S"
    r = _pedir("GET", "/history/activity", parametros={
        "from": datetime.fromtimestamp(desde_marca_tiempo, timezone.utc).strftime(formato),
        "to": datetime.fromtimestamp(hasta_marca_tiempo, timezone.utc).strftime(formato),
        "dealId": deal_id, "detailed": "true"})
    if r is None or r.status_code != 200:
        return []
    return [a for a in r.json().get("activities", []) if a.get("dealId") == deal_id]


# TITULO DETALLE CIERRE

def detalle_cierre(deal_id: str, t_cierre: float) -> dict:
    """Detalle de una operación cerrada: {"epic","tipo","volumen"(lotes),"entrada","salida","hora_in"}.
    `t_cierre` = epoch UTC del cierre. {} si Capital no lo entrega (se reintenta en la próxima carga)."""
    if not deal_id or not t_cierre:
        return {}
    if deal_id in _cierres:
        return _cierres[deal_id]
    cierre = None
    for a in _actividad(deal_id, t_cierre - 3600, t_cierre + 3600):
        d = a.get("details", {}) or {}
        if a.get("type") == "POSITION" and d.get("openPrice") is not None:
            cierre = a
            break
    if not cierre:
        return {}
    d = cierre["details"]
    epic = cierre.get("epic", "")
    # El registro del cierre trae la dirección CONTRARIA a la de la operación (se cierra una compra vendiendo).
    tipo = "Venta" if str(d.get("direction", "")).upper() == "BUY" else "Compra"
    hora_in = 0
    # Hora de apertura: se busca hacia atrás, por ventanas de 24 h, el registro de apertura (sin openPrice).
    for k in range(0, 15):
        fin = t_cierre - k * 86400
        for a in _actividad(deal_id, fin - 86400, fin):
            if a.get("type") == "POSITION" and (a.get("details", {}) or {}).get("openPrice") is None:
                hora_in = _epoch_utc(a.get("dateUTC", "") or a.get("date", ""))
                break
        if hora_in:
            break
    resultado = {"epic": epic, "tipo": tipo,
           "volumen": float(d.get("size", 0.0) or 0.0) / factor_lote_epic(epic),
           "entrada": float(d.get("openPrice", 0.0) or 0.0), "salida": float(d.get("level", 0.0) or 0.0),
           "hora_in": int(hora_in)}
    with _CANDADO_CIERRES:
        _cierres[deal_id] = resultado
        try:
            tmp = _RUTA_CIERRES + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(_cierres, f)
            os.replace(tmp, _RUTA_CIERRES)
        except Exception:
            pass
    return resultado


_cargar_cierres()


# TITULO OBTENER PRECIO ACTUAL

# ---------------------------------------------------------------------------
# Precios e histórico de velas
# ---------------------------------------------------------------------------
def obtener_precio_actual(symbol: str) -> dict:
    """Bid/Ask del instrumento (snapshot del mercado). Cacheado ~3 s por epic."""
    epic = resolver_simbolo(symbol)
    _ahora = time.time()
    _v = _cache_con_refresco(f"precio:{epic}", _TIEMPO_VIDA_PRECIO, obtener_precio_actual, symbol)
    if _v is not None:
        return _v
    r = _pedir("GET", f"/markets/{epic}")
    if r is None or r.status_code != 200:
        return {"error": f"No se pudo obtener el precio para {epic}"}
    snap = r.json().get("snapshot", {}) or {}
    bid = float(snap.get("bid", 0.0) or 0.0)
    ask = float(snap.get("offer", 0.0) or 0.0)
    if not (bid or ask):
        return {"error": f"No se pudo obtener el precio para {epic}"}
    _resultado = {
        "symbol": epic,
        "bid": bid,
        "ask": ask,
        "last": bid or ask,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    _cache_lectura[f"precio:{epic}"] = (_ahora, _resultado)
    return _resultado


# TITULO PRECARGAR PRECIOS

def precargar_precios(symbols) -> None:
    """Pide el Bid/Ask de VARIOS instrumentos en UNA sola llamada (GET /markets?epics=...)
    y llena la caché de precios, para que el render inicial no haga N llamadas en serie.
    Capital admite hasta 50 epics por llamada."""
    epics = []
    for s in symbols or []:
        e = resolver_simbolo(s)
        if e and e not in epics:
            epics.append(e)
    _ahora = time.time()
    for i in range(0, len(epics), 50):
        lote = epics[i:i + 50]
        r = _pedir("GET", "/markets", parametros={"epics": ",".join(lote)})
        if r is None or r.status_code != 200:
            continue
        data = r.json()
        for m in data.get("marketDetails", data.get("markets", [])):
            inst = m.get("instrument", {}) or {}
            snap = m.get("snapshot", {}) or {}
            epic = inst.get("epic") or m.get("epic")
            bid = snap.get("bid", m.get("bid"))
            ask = snap.get("offer", m.get("offer"))
            if not epic or bid is None:
                continue
            bid = float(bid or 0.0)
            ask = float(ask or 0.0)
            _cache_lectura[f"precio:{epic}"] = (_ahora, {
                "symbol": epic, "bid": bid, "ask": ask, "last": bid or ask,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})


# Capital.com rechaza max > 1000 (error.invalid.max). El gráfico puede pedir más
# (p. ej. 1500); se recorta para que la petición no falle y devuelva 0 velas.
_MAX_VELAS_CAPITAL = 1000


# TITULO VELAS CRUDAS

def _velas_crudas(epic: str, resolucion: str, maximo: int = None,
                  desde: str = None, hasta: str = None) -> list:
    """Pide velas OHLC a Capital (GET /prices) y devuelve la lista tal como llega.

    Recibe el epic, la resolución y, opcionalmente, la cantidad máxima y el rango de fechas. Usa una caché corta según la resolución para no repetir consultas idénticas.
    """
    parametros = {"resolution": resolucion}
    if maximo:
        parametros["max"] = min(int(maximo), _MAX_VELAS_CAPITAL)
    if desde:
        parametros["from"] = desde
    if hasta:
        parametros["to"] = hasta
    # Caché corta por resolución: las velas de minuto casi no se cachean (el gráfico las quiere frescas); las de
    # hora/día sí. Evita repetir la misma consulta (Mercados pide cierre previo y series de muchos instrumentos).
    tiempo_vida = 3.0 if resolucion == "MINUTE" else (15.0 if resolucion.startswith("MINUTE") else
                                              (120.0 if resolucion == "DAY" else 60.0))
    clave = f"velas:{epic}:{resolucion}:{parametros.get('max')}:{desde}:{hasta}"
    impacto = _cache_lectura.get(clave)
    if impacto and (time.time() - impacto[0]) < tiempo_vida:
        return impacto[1]
    r = _pedir("GET", f"/prices/{epic}", parametros=parametros)
    if r is None or r.status_code != 200:
        return []
    datos = r.json().get("prices", [])
    if datos:
        _cache_lectura[clave] = (time.time(), datos)
    return datos


# TITULO MID

def _medio(precio: dict) -> float:
    """Precio BID de una pieza open/close/high/low de la vela (como MT5 y como los ticks en vivo:
    así la vela que se mueve con los ticks y la que llega por REST no difieren en el spread)."""
    b = precio.get("bid"); a = precio.get("ask")
    if b is not None:
        return float(b)
    return float(a if a is not None else 0.0)


# TITULO OBTENER DATOS HISTORICOS

def obtener_datos_historicos(symbol: str, timeframe=TIMEFRAME_H1, n_velas: int = 100) -> pd.DataFrame:
    """OHLCV histórico como DataFrame indexado por tiempo (equivalente a MT5)."""
    epic = resolver_simbolo(symbol)
    resultado = _resolucion(timeframe)
    velas = _velas_crudas(epic, resultado, maximo=int(n_velas))
    if not velas:
        return pd.DataFrame()
    filas = []
    for v in velas:
        filas.append({
            "time": pd.to_datetime(v.get("snapshotTimeUTC") or v.get("snapshotTime")),
            "open": _medio(v.get("openPrice", {})),
            "high": _medio(v.get("highPrice", {})),
            "low": _medio(v.get("lowPrice", {})),
            "close": _medio(v.get("closePrice", {})),
            "tick_volume": v.get("lastTradedVolume", 0),
        })
    tabla_datos = pd.DataFrame(filas).set_index("time")
    return tabla_datos


# TITULO OBTENER VELAS RANGO

def obtener_velas_rango(symbol: str, marca_tiempo_desde: float, marca_tiempo_hasta: float) -> list:
    """Velas OHLC que cubren [ts_desde, ts_hasta] (epoch), para el mini-gráfico del
    Trading Journal. Elige la resolución según la duración (~40-120 velas)."""
    # Blindaje: timestamps inválidos (<=0) darían un inicio negativo y datetime.fromtimestamp
    # revienta en Windows (OSError 22). Sin rango útil no se dibuja nada.
    if not marca_tiempo_hasta or float(marca_tiempo_hasta) <= 0:
        return []
    duracion = max(60.0, float(marca_tiempo_hasta) - float(marca_tiempo_desde))
    pad = duracion * 0.35 + 300
    d0, d1 = float(marca_tiempo_desde) - pad, float(marca_tiempo_hasta) + pad
    d0 = max(d0, 86400.0)      # nunca antes de 1970 (evita OSError en Windows)
    objetivo = (d1 - d0) / 60.0
    escala = ["MINUTE", "MINUTE_5", "MINUTE_15", "HOUR", "HOUR_4", "DAY"]
    resultado = escala[0]
    for r_ in escala:
        resultado = r_
        if _segundos_resolucion(r_) >= objetivo:
            break
    epic = resolver_simbolo(symbol)
    desde = datetime.fromtimestamp(d0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    hasta = datetime.fromtimestamp(d1, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    velas = _velas_crudas(epic, resultado, desde=desde, hasta=hasta, maximo=1000)
    out = []
    for v in velas:
        t = _epoch_utc(v.get("snapshotTimeUTC") or v.get("snapshotTime"))
        out.append({"t": t, "o": _medio(v.get("openPrice", {})), "h": _medio(v.get("highPrice", {})),
                    "l": _medio(v.get("lowPrice", {})), "c": _medio(v.get("closePrice", {}))})
    return out


# TITULO CONFIRMAR

# ---------------------------------------------------------------------------
# Órdenes
# ---------------------------------------------------------------------------
def _confirmar(dealReference: str) -> dict:
    """GET /confirms/{ref}: comprueba si la orden fue ACEPTADA y devuelve el dealId."""
    if not dealReference:
        return {"error": "Sin dealReference que confirmar"}
    time.sleep(0.3)  # dar un instante a que la orden se procese
    r = _pedir("GET", f"/confirms/{dealReference}")
    if r is None or r.status_code != 200:
        return {"error": f"No se pudo confirmar la orden ({dealReference})"}
    d = r.json()
    estado = str(d.get("dealStatus", "")).upper()
    if estado != "ACCEPTED":
        motivo = d.get("reason") or d.get("status") or estado or "rechazada"
        return {"error": f"Orden no aceptada: {motivo}"}
    dealId = d.get("dealId", "")
    for a in d.get("affectedDeals", []):
        if a.get("status") in ("OPENED", "FULLY_CLOSED", "AMENDED"):
            dealId = a.get("dealId", dealId)
    return {"ok": True, "dealId": dealId, "level": d.get("level"), "size": d.get("size")}


# TITULO EJECUTAR ORDEN MERCADO

def ejecutar_orden_mercado(symbol: str, tipo: str, volumen: float, stop_loss: float = 0.0, take_profit: float = 0.0) -> dict:
    """Orden a mercado (BUY/SELL). Abre una posición en Capital.com."""
    epic = resolver_simbolo(symbol)
    cuerpo = {"epic": epic, "direction": tipo.upper(), "size": round(float(volumen) * factor_lote_epic(epic), 6)}
    if stop_loss and stop_loss > 0:
        cuerpo["stopLevel"] = float(stop_loss)
    if take_profit and take_profit > 0:
        cuerpo["profitLevel"] = float(take_profit)
    with _ORDEN_CANDADO:
        r = _pedir("POST", "/positions", json=cuerpo)
    if r is None:
        return {"error": "Sin conexión con Capital.com"}
    if r.status_code >= 400:
        return {"error": f"Fallo al enviar orden (HTTP {r.status_code}): {r.text}"}
    configuracion = _confirmar(r.json().get("dealReference", ""))
    if "error" in configuracion:
        return configuracion
    # Trading Journal: guarda el plan (entrada + SL + TP) ligado a la posición.
    if (stop_loss and stop_loss > 0) or (take_profit and take_profit > 0):
        try:
            from herramientas import almacen_diario
            almacen_diario.guardar_plan(configuracion["dealId"], configuracion.get("level") or 0.0, stop_loss, take_profit,
                                        tipo.upper(), epic, float(volumen))
        except Exception:
            pass
    _invalidar()
    return {"status": "success", "order": configuracion["dealId"], "price": configuracion.get("level") or 0.0,
            "volume": float(volumen), "symbol": epic}


# TITULO COLOCAR ORDEN PENDIENTE

def colocar_orden_pendiente(symbol: str, tipo: str, volumen: float, precio: float,
                            stop_loss: float = 0.0, take_profit: float = 0.0,
                            hasta_cancelar: bool = True) -> dict:
    """Orden pendiente "al llegar a este precio" (working order).
    El tipo (LIMIT/STOP) se deduce igual que en MT5, según el precio vs mercado:
      COMPRA bajo el ask -> Buy Limit · sobre el ask -> Buy Stop
      VENTA sobre el bid -> Sell Limit · bajo el bid -> Sell Stop"""
    epic = resolver_simbolo(symbol)
    precio_actual = obtener_precio_actual(epic)
    if "error" in precio_actual:
        return {"error": precio_actual["error"]}
    compra = tipo.upper() == "BUY"
    referencia = precio_actual["ask"] if compra else precio_actual["bid"]
    if compra:
        tipo_orden, nombre = ("LIMIT", "Buy Limit") if precio < referencia else ("STOP", "Buy Stop")
    else:
        tipo_orden, nombre = ("LIMIT", "Sell Limit") if precio > referencia else ("STOP", "Sell Stop")
    cuerpo = {"epic": epic, "direction": tipo.upper(), "size": round(float(volumen) * factor_lote_epic(epic), 6),
              "level": float(precio), "type": tipo_orden}
    if stop_loss and stop_loss > 0:
        cuerpo["stopLevel"] = float(stop_loss)
    if take_profit and take_profit > 0:
        cuerpo["profitLevel"] = float(take_profit)
    if not hasta_cancelar:   # solo hoy (DAY): caduca al final del día UTC
        fin = datetime.now(timezone.utc).replace(hour=23, minute=59, second=0, microsecond=0)
        cuerpo["goodTillDate"] = fin.strftime("%Y-%m-%dT%H:%M:%S")
    with _ORDEN_CANDADO:
        r = _pedir("POST", "/workingorders", json=cuerpo)
    if r is None:
        return {"error": "Sin conexión con Capital.com"}
    if r.status_code >= 400:
        return {"error": f"Fallo al colocar la orden pendiente (HTTP {r.status_code}): {r.text}"}
    configuracion = _confirmar(r.json().get("dealReference", ""))
    if "error" in configuracion:
        return configuracion
    _invalidar()
    return {"status": "success", "order": configuracion["dealId"], "price": float(precio),
            "volume": float(volumen), "symbol": epic, "tipo": nombre}


# TITULO CERRAR POSICION

def cerrar_posicion(ticket) -> dict:
    """Cierra una posición abierta por su dealId."""
    elemento = _buscar_posicion(ticket)
    p = elemento.get("position", {}) if elemento else {}
    symbol = elemento.get("market", {}).get("epic", "") if elemento else ""
    profit = float(p.get("upl", 0.0) or 0.0)
    with _ORDEN_CANDADO:
        r = _pedir("DELETE", f"/positions/{ticket}")
    if r is None:
        return {"error": "Sin conexión con Capital.com"}
    if r.status_code >= 400:
        return {"error": f"Fallo al cerrar (HTTP {r.status_code}): {r.text}"}
    configuracion = _confirmar(r.json().get("dealReference", ""))
    if "error" in configuracion:
        return configuracion
    _invalidar()
    return {"status": "success", "profit": profit, "symbol": symbol}


# TITULO NIVELES ACTUALES

def _niveles_actuales(ticket) -> tuple:
    """(stopLevel, profitLevel) vigentes de una posición (0.0 = sin nivel)."""
    elemento = _buscar_posicion(ticket)
    p = elemento.get("position", {}) if elemento else {}
    return float(p.get("stopLevel", 0.0) or 0.0), float(p.get("profitLevel", 0.0) or 0.0)


# TITULO MODIFICAR SLTP

def modificar_sltp(ticket, stop_loss=None, take_profit=None) -> dict:
    """Cambia el Stop Loss / Take Profit de una posición abierta.
    None = deja el valor actual · 0 = QUITA ese nivel. Capital reemplaza ambos niveles en cada
    PUT (lo que no se envía se elimina), así que siempre se mandan los dos ya combinados."""
    if stop_loss is None and take_profit is None:
        return {"error": "Nada que modificar"}
    stop_loss_act, take_profit_act = _niveles_actuales(ticket)
    stop_loss_nuevo = stop_loss_act if stop_loss is None else float(stop_loss)
    take_profit_nuevo = take_profit_act if take_profit is None else float(take_profit)
    cuerpo = {}
    if stop_loss_nuevo > 0:
        cuerpo["stopLevel"] = stop_loss_nuevo
    if take_profit_nuevo > 0:
        cuerpo["profitLevel"] = take_profit_nuevo
    with MT5_LOCK:
        r = _pedir("PUT", f"/positions/{ticket}", json=cuerpo)
    if r is None:
        return {"error": "Sin conexión con Capital.com"}
    if r.status_code >= 400:
        return {"error": f"No se pudo modificar (HTTP {r.status_code}): {r.text}"}
    configuracion = _confirmar(r.json().get("dealReference", ""))
    if "error" in configuracion:
        return configuracion
    _invalidar()
    return {"status": "success", "ticket": ticket,
            "sl": cuerpo.get("stopLevel", 0.0), "tp": cuerpo.get("profitLevel", 0.0)}


_NOMBRE_PENDIENTE = {"LIMIT": "Limit", "STOP": "Stop"}


# TITULO MODIFICAR ORDEN

def modificar_orden(ticket, precio=None, stop_loss=None, take_profit=None,
                    caducidad=None, expiracion=None) -> dict:
    """Modifica una orden PENDIENTE (precio de entrada, SL, TP y/o caducidad)."""
    # Capital reemplaza los niveles en cada PUT (lo no enviado se elimina): se parte de los vigentes.
    # None = conserva el valor actual · 0 = quita ese nivel.
    actual = {}
    r0 = _pedir("GET", "/workingorders")
    if r0 is not None and r0.status_code == 200:
        for it in r0.json().get("workingOrders", []):
            w = it.get("workingOrderData", it) or {}
            if str(w.get("dealId")) == str(ticket):
                actual = w
                break
    cuerpo = {}
    nivel = float(precio) if precio is not None else float(actual.get("orderLevel", 0.0) or 0.0)
    if nivel > 0:
        cuerpo["level"] = nivel
    stop_loss_n = float(stop_loss) if stop_loss is not None else float(actual.get("stopLevel", 0.0) or 0.0)
    take_profit_n = float(take_profit) if take_profit is not None else float(actual.get("profitLevel", 0.0) or 0.0)
    if stop_loss_n > 0:
        cuerpo["stopLevel"] = stop_loss_n
    if take_profit_n > 0:
        cuerpo["profitLevel"] = take_profit_n
    if actual.get("goodTillDate") and caducidad is None:
        cuerpo["goodTillDate"] = actual["goodTillDate"]
    if caducidad == "day":
        fin = datetime.now(timezone.utc).replace(hour=23, minute=59, second=0, microsecond=0)
        cuerpo["goodTillDate"] = fin.strftime("%Y-%m-%dT%H:%M:%S")
    elif caducidad == "specified" and expiracion:
        cuerpo["goodTillDate"] = datetime.fromtimestamp(
            int(expiracion), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    if not cuerpo:
        return {"error": "Nada que modificar"}
    with MT5_LOCK:
        r = _pedir("PUT", f"/workingorders/{ticket}", json=cuerpo)
    if r is None:
        return {"error": "Sin conexión con Capital.com"}
    if r.status_code >= 400:
        return {"error": f"No se pudo modificar la orden (HTTP {r.status_code}): {r.text}"}
    configuracion = _confirmar(r.json().get("dealReference", ""))
    if "error" in configuracion:
        return configuracion
    _invalidar()
    return {"status": "success", "ticket": ticket, "price": cuerpo.get("level", 0.0),
            "sl": cuerpo.get("stopLevel", 0.0), "tp": cuerpo.get("profitLevel", 0.0)}


# TITULO ELIMINAR ORDEN

def eliminar_orden(ticket) -> dict:
    """Cancela una orden PENDIENTE (working order)."""
    with MT5_LOCK:
        r = _pedir("DELETE", f"/workingorders/{ticket}")
    if r is None:
        return {"error": "Sin conexión con Capital.com"}
    if r.status_code >= 400:
        return {"error": f"No se pudo cancelar la orden (HTTP {r.status_code}): {r.text}"}
    configuracion = _confirmar(r.json().get("dealReference", ""))
    if "error" in configuracion:
        return configuracion
    _invalidar()
    return {"status": "success", "ticket": ticket, "tipo": "", "symbol": ""}


# TITULO OBTENER DOM

# ---------------------------------------------------------------------------
# Profundidad de mercado (DOM): no disponible por REST en Capital.com
# ---------------------------------------------------------------------------
def obtener_dom(symbol: str, niveles: int = 8) -> dict:
    """Profundidad de mercado: Capital no la entrega por REST, así que devuelve listas vacías con `disponible` en False. El nivel 1 sale del streaming (`/dom` del servidor de datos)."""
    return {"ask": [], "bid": [], "disponible": False,
            "motivo": "Capital.com no entrega libro de órdenes (DOM) por su API REST."}


# -------------------------------------------------------------------------------------------------------
# ------------------------------------- FIN Piña y Jara capital .PY -------------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
