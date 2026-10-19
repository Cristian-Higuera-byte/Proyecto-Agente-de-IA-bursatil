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

import calendar
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

# El .env del proyecto manda sobre las variables de entorno del sistema: `load_dotenv()` a secas NO pisa una variable que ya exista
# (por ejemplo una CAPITAL_API_KEY antigua de Windows), y entonces se enviaba una clave distinta a la del .env.
_VARIABLES_CAPITAL = ("CAPITAL_DEMO", "CAPITAL_API_KEY", "CAPITAL_IDENTIFIER", "CAPITAL_API_PASSWORD")
_previas = {k: os.environ.get(k) for k in _VARIABLES_CAPITAL}
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"), override=True)
for _k, _v in _previas.items():
    if _v and os.environ.get(_k) != _v:
        print(f"[CAPITAL] Aviso: la variable de entorno del sistema {_k} era distinta a la del .env; se usa la del .env.")

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
_ES_DEMO = os.getenv("CAPITAL_DEMO", "true").strip().lower() in ("true", "1", "si", "sí")
BASE = ("https://demo-api-capital.backend-capital.com/api/v1" if _ES_DEMO
        else "https://api-capital.backend-capital.com/api/v1")
_API_KEY = os.getenv("CAPITAL_API_KEY", "").strip()
_IDENTIFIER = os.getenv("CAPITAL_IDENTIFIER", "").strip()
_API_PASSWORD = os.getenv("CAPITAL_API_PASSWORD", "").strip()

class _SinCandado:
    """Candado que no bloquea nunca: cumple la interfaz de `threading.RLock` (with, acquire, release) sin esperar a nadie.

    La API de MetaTrader 5 no admite varios hilos a la vez, por eso en la versión MT5 todas las lecturas pasaban por un
    candado global. La API REST de Capital.com sí admite peticiones simultáneas, y mantener ese candado durante una llamada
    de 300-800 ms hacía que cualquier otra lectura (velas, cuenta, precios) esperara a las demás, y hasta quedara sin
    respuesta si el motor volvía a tomarlo sin parar. El límite de peticiones por segundo lo controla `_limitar()`."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def acquire(self, *args, **kwargs):
        return True

    def release(self):
        return None


# Nombre heredado del puente MT5: muchos módulos hacen `with MT5_LOCK:` al leer. Con Capital.com no serializa nada.
MT5_LOCK = _SinCandado()
# Las operaciones que modifican órdenes y posiciones (leer niveles y luego enviar el cambio) sí se serializan entre sí.
_ORDER_LOCK = threading.RLock()

# Caché de lecturas (cuenta, precio, posiciones): como cada llamada REST a Capital
# tarda ~300-500 ms y el dashboard re-ejecuta toda la página en cada interacción,
# se cachean unos segundos. El precio/P-G EN VIVO llega por SSE/WebSocket, así que
# un desfase de pocos segundos en estas lecturas no se nota.
_cache_lectura: dict = {}          # clave -> (ts, valor)
_TTL_CUENTA = 2.0
_TTL_PRECIO = 3.0
_TTL_POSICIONES = 2.0
_STALE_MAX = 120.0                 # una lectura vencida se sirve al instante (y se refresca aparte) hasta esta edad
_refrescando: set = set()
_tl = threading.local()


def _cache_swr(clave, ttl, fn, *args):
    """Caché "stale-while-revalidate": devuelve el valor vigente; si venció (pero es reciente) lo devuelve
    igual AL INSTANTE y lo refresca en un hilo aparte, para que ningún rerun de la página espere ~300 ms
    por cada llamada REST (los valores en vivo ya llegan por el WebSocket). None = no hay caché utilizable."""
    hit = _cache_lectura.get(clave)
    if not hit or getattr(_tl, "bg", False):
        return None
    edad = time.time() - hit[0]
    if edad < ttl:
        return hit[1]
    if edad < _STALE_MAX:
        if clave not in _refrescando:
            _refrescando.add(clave)

            def _run():
                _tl.bg = True
                try:
                    fn(*args)
                except Exception:
                    pass
                finally:
                    _refrescando.discard(clave)
            threading.Thread(target=_run, daemon=True).start()
        return hit[1]
    return None


def get_mercado(epic: str) -> dict:
    """GET /markets/{epic} (JSON crudo) con caché 30 s + refresco en segundo plano. {} si falla.
    Lo comparten especs_posicion y el shim (symbol_info): una sola llamada por instrumento."""
    clave = f"mercado:{epic}"
    v = _cache_swr(clave, 30.0, get_mercado, epic)
    if v is not None:
        return v
    r = _pedir("GET", f"/markets/{epic}")
    data = r.json() if (r is not None and r.status_code == 200) else {}
    if data:
        _cache_lectura[clave] = (time.time(), data)
    return data


def leer_json(ruta: str, ttl: float = 2.0, params: dict = None):
    """GET `ruta` y devuelve el JSON (o None si falla), con caché corta + refresco en segundo plano.
    Para lecturas repetidas en cada rerun de la página (/positions, /workingorders, /history/...)."""
    clave = f"raw:{ruta}:{sorted((params or {}).items())}"
    v = _cache_swr(clave, ttl, leer_json, ruta, ttl, params)
    if v is not None:
        return v
    r = _pedir("GET", ruta, params=params)
    if r is None or r.status_code != 200:
        return None
    data = r.json()
    _cache_lectura[clave] = (time.time(), data)
    return data


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
_LOCK_SESION = threading.RLock()   # solo serializa la apertura/renovación de la sesión

_TIMEOUT = 15

# ---------------------------------------------------------------------------
# Control de la sesión y del ritmo de peticiones
# ---------------------------------------------------------------------------
# Capital.com admite 1 POST /session por segundo y unas 10 peticiones por segundo en total; si se insiste responde
# HTTP 429 y cada intento rechazado alarga el castigo. Antes, con la sesión caída, el motor (cada 0,5 s), el WebSocket,
# cada rerun de Streamlit y los dos procesos (dashboard y servidor de datos) pedían sesión sin descanso: cientos de
# intentos por minuto. Ahora:
#   1. Tras un rechazo se espera (la que indique Retry-After o 10 s, 20 s, 40 s, 80 s, 160 s, 5 min) y durante la espera NO se
#      llama a la API: las lecturas devuelven "sin conexión" al instante y el aviso se imprime una sola vez.
#   2. La sesión y la espera se comparten entre procesos con data/capital_sesion.json: el segundo proceso adopta la
#      sesión abierta por el primero en vez de abrir otra, y un candado de archivo evita que ambos la pidan a la vez.
#   3. Un 401 solo reabre la sesión si nadie la renovó ya (antes cada hilo con 401 reabría una).
#   4. Un limitador deja pasar como máximo _MAX_PETICIONES_S peticiones por segundo en cada proceso: 6 para el dashboard (que
#      concentra las ráfagas al abrir vistas) y 4 para el servidor de datos (`fijar_limite_peticiones`), 10 en total, el tope de
#      Capital. Las peticiones de segundo plano (precargas y refrescos) solo pueden usar la mitad de ese cupo, así que una acción
#      del usuario nunca espera detrás de ellas.
_MIN_ENTRE_SESIONES = 2.0               # s mínimos entre dos POST /session de este proceso
_ESPERAS_RECHAZO = (10, 20, 40, 80, 160, 300)   # s de pausa tras el 1.º, 2.º... rechazo seguido (429 u otro)
_ESPERA_CREDENCIALES = 300              # s de pausa si Capital rechaza las credenciales
_MAX_PETICIONES_S = 6                   # límite propio de este proceso (el de Capital es 10 por segundo en total); el servidor de datos baja el suyo a 4
_espera_hasta = 0.0                     # epoch hasta el que NO se pide sesión
_fallos_sesion = 0
_ultimo_intento = 0.0
_ultimo_aviso = 0.0
_ultimo_guardado = 0.0
_INTERVALO_GUARDADO_S = 30
_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ARCHIVO_SESION = os.path.join(_RAIZ, "data", "capital_sesion.json")   # data/*.json no se sube al repositorio
_ARCHIVO_CANDADO = _ARCHIVO_SESION + ".lock"
_marcas_peticion: list = []
_marcas_fondo: list = []
_LOCK_RITMO = threading.Lock()


def _aviso(msg: str) -> None:
    """Imprime un aviso como máximo una vez cada 30 s, para no inundar la consola."""
    global _ultimo_aviso
    if time.time() - _ultimo_aviso >= 30:
        _ultimo_aviso = time.time()
        print(msg)


def _leer_archivo() -> dict:
    """Lee la sesión compartida entre procesos; {} si no existe o no se puede leer."""
    try:
        with open(_ARCHIVO_SESION, "r", encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _guardar_archivo() -> None:
    """Guarda la sesión y la espera actuales para que otros procesos las reutilicen (escritura atómica)."""
    global _ultimo_guardado
    _ultimo_guardado = time.time()
    try:
        os.makedirs(os.path.dirname(_ARCHIVO_SESION), exist_ok=True)
        tmp = _ARCHIVO_SESION + f".{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"CST": _tokens["CST"], "X-SECURITY-TOKEN": _tokens["X-SECURITY-TOKEN"], "ts": _ultimo_uso,
                       "cuenta": _cuenta_activa_id, "espera_hasta": _espera_hasta}, fh)
        os.replace(tmp, _ARCHIVO_SESION)
    except Exception:
        pass


def _adoptar_archivo(excluir_cst: str = "") -> bool:
    """Usa la sesión que otro proceso dejó en el archivo si sigue vigente y no es `excluir_cst` (la que acaba de fallar).

    También hereda la pausa compartida. Devuelve True si quedó una sesión válida en memoria."""
    global _ultimo_uso, _cuenta_activa_id, _espera_hasta
    d = _leer_archivo()
    if not d:
        return False
    if float(d.get("espera_hasta", 0) or 0) > _espera_hasta:
        _espera_hasta = float(d["espera_hasta"])
    cst, xst, ts = d.get("CST", ""), d.get("X-SECURITY-TOKEN", ""), float(d.get("ts", 0) or 0)
    if cst and xst and cst != excluir_cst and (time.time() - ts) < _VIDA_TOKEN_S:
        _tokens["CST"], _tokens["X-SECURITY-TOKEN"] = cst, xst
        _cuenta_activa_id = d.get("cuenta", "") or _cuenta_activa_id
        _ultimo_uso = max(_ultimo_uso, ts)
        return True
    return False


class _CandadoArchivo:
    """Candado entre procesos: solo uno pide sesión a la vez; los demás esperan (hasta 6 s) y luego la adoptan."""

    def __enter__(self):
        self.tengo = False
        limite = time.time() + 6
        while time.time() < limite:
            try:
                fd = os.open(_ARCHIVO_CANDADO, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                self.tengo = True
                break
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(_ARCHIVO_CANDADO) > 20:   # candado huérfano de un proceso caído
                        os.remove(_ARCHIVO_CANDADO)
                        continue
                except OSError:
                    pass
                time.sleep(0.2)
            except OSError:
                break
        return self

    def __exit__(self, *exc):
        if self.tengo:
            try:
                os.remove(_ARCHIVO_CANDADO)
            except OSError:
                pass
        return False


def _pausar(segundos: float, motivo: str) -> None:
    """Deja de pedir sesión durante `segundos`, lo comparte con los demás procesos y avisa (con límite de frecuencia)."""
    global _espera_hasta
    _espera_hasta = time.time() + segundos
    _guardar_archivo()
    _aviso(f"[CAPITAL] {motivo} Pausa de {int(segundos)} s antes de volver a intentarlo (no se llama a la API mientras tanto).")


def _rechazo_sesion(r) -> None:
    """Decide la pausa tras un POST /session rechazado: Retry-After si Capital lo envía; si no, una espera creciente.

    Las credenciales inválidas (HTTP 401 o errorCode `invalid`) esperan más, porque reintentar no sirve de nada."""
    global _fallos_sesion
    texto = (r.text or "")[:200]
    if r.status_code == 401 or "invalid" in texto.lower():
        extra = ""
        if "invalid.api.key" in texto:
            extra = (f" La API key enviada tiene {len(_API_KEY)} caracteres ({_API_KEY[:2]}…{_API_KEY[-2:]}) y se usa el entorno "
                     f"{'DEMO' if _ES_DEMO else 'REAL'}: compárala con la de Capital.com (Configuración → API integrations).")
        _pausar(_ESPERA_CREDENCIALES, f"Capital.com rechazó las credenciales (HTTP {r.status_code}: {texto}). Revisa el .env.{extra}")
        return
    try:
        espera = float(r.headers.get("Retry-After", ""))
    except (TypeError, ValueError):
        espera = float(_ESPERAS_RECHAZO[min(_fallos_sesion, len(_ESPERAS_RECHAZO) - 1)])
    _fallos_sesion += 1
    _pausar(espera, f"Falló la sesión (HTTP {r.status_code}): {texto}.")


def _invalidar_archivo(cst: str) -> None:
    """Borra el archivo de sesión compartida si todavía guarda el token `cst` (que Capital acaba de rechazar), para que
    ningún proceso vuelva a adoptar una sesión muerta."""
    if cst and _leer_archivo().get("CST") == cst:
        try:
            os.remove(_ARCHIVO_SESION)
        except OSError:
            pass


def _abrir_sesion(excluir_cst: str = "") -> bool:
    """POST /session -> guarda CST y X-SECURITY-TOKEN. Devuelve True si conecta.

    No llama a la API durante una pausa; primero intenta adoptar la sesión abierta por otro proceso (distinta de
    `excluir_cst`, la que acaba de fallar); y serializa la petición real con un candado de archivo y un mínimo de
    `_MIN_ENTRE_SESIONES` segundos entre intentos."""
    global _ultimo_uso, _cuenta_activa_id, _espera_hasta, _fallos_sesion, _ultimo_intento
    if not (_API_KEY and _IDENTIFIER and _API_PASSWORD):
        _aviso("[CAPITAL] Faltan credenciales en el .env "
               "(CAPITAL_API_KEY / CAPITAL_IDENTIFIER / CAPITAL_API_PASSWORD).")
        return False
    if _adoptar_archivo(excluir_cst) and _tokens["CST"]:
        return True
    if time.time() < _espera_hasta:
        return False
    with _CandadoArchivo():
        if _adoptar_archivo(excluir_cst) and _tokens["CST"]:      # la abrió otro proceso mientras esperábamos el candado
            return True
        if time.time() < _espera_hasta:
            return False
        pausa = _MIN_ENTRE_SESIONES - (time.time() - _ultimo_intento)
        if pausa > 0:
            time.sleep(pausa)
        _ultimo_intento = time.time()
        try:
            r = _HTTP.post(
                f"{BASE}/session",
                headers={"X-CAP-API-KEY": _API_KEY, "Content-Type": "application/json"},
                json={"identifier": _IDENTIFIER, "password": _API_PASSWORD,
                      "encryptedPassword": False},
                timeout=_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            _pausar(10, f"No se pudo contactar a Capital.com: {e}.")
            return False
        if r.status_code != 200:
            _rechazo_sesion(r)
            return False
        _tokens["CST"] = r.headers.get("CST", "")
        _tokens["X-SECURITY-TOKEN"] = r.headers.get("X-SECURITY-TOKEN", "")
        try:
            _cuenta_activa_id = r.json().get("accountId", "")
        except Exception:
            _cuenta_activa_id = ""
        _ultimo_uso = time.time()
        _fallos_sesion = 0
        _espera_hasta = 0.0
        _guardar_archivo()
        return bool(_tokens["CST"] and _tokens["X-SECURITY-TOKEN"])


def inicializar_mt5(login=None, password=None, server=None) -> bool:
    """Compat: asegura una sesión activa con Capital.com (nombre heredado del puente).

    Los parámetros login/password/server se ignoran (eran de MT5); las credenciales
    salen del .env. Renueva la sesión si está por caducar y, si Capital la rechazó hace poco,
    devuelve False al instante sin llamar a la API (ver «Control de la sesión»)."""
    # Vía rápida SIN candado: con sesión vigente las lecturas no se esperan entre sí.
    if _tokens["CST"] and (time.time() - _ultimo_uso) < _VIDA_TOKEN_S:
        return True
    if time.time() < _espera_hasta and not _adoptar_archivo():
        return False
    with _LOCK_SESION:
        if _tokens["CST"] and (time.time() - _ultimo_uso) < _VIDA_TOKEN_S:
            return True
        return _abrir_sesion()


def cerrar_mt5():
    """Compat: cierra la sesión con Capital.com."""
    with MT5_LOCK:
        try:
            if _tokens["CST"]:
                _HTTP.delete(f"{BASE}/session", headers=_cabeceras(), timeout=_TIMEOUT)
        except Exception:
            pass
        if _leer_archivo().get("CST") == _tokens["CST"]:
            try:
                os.remove(_ARCHIVO_SESION)
            except OSError:
                pass
        _tokens["CST"] = _tokens["X-SECURITY-TOKEN"] = ""


def _cabeceras() -> dict:
    return {"CST": _tokens["CST"], "X-SECURITY-TOKEN": _tokens["X-SECURITY-TOKEN"]}


def fijar_limite_peticiones(por_segundo: int) -> None:
    """Cambia el máximo de peticiones por segundo de ESTE proceso. El servidor de datos lo baja a 4 para que, sumado al dashboard
    (6), nunca se supere el tope de 10 por segundo que Capital.com aplica a la sesión compartida."""
    global _MAX_PETICIONES_S
    _MAX_PETICIONES_S = max(1, int(por_segundo))


def marcar_hilo_fondo() -> None:
    """Marca el hilo actual como de segundo plano (precargas y refrescos): sus peticiones usan solo la mitad del cupo por segundo,
    de modo que una acción del usuario no espere detrás de ellas."""
    _tl.bg = True


def _limitar() -> None:
    """Limitador de ritmo: deja pasar como máximo `_MAX_PETICIONES_S` peticiones en cualquier ventana de 1 s, y las de segundo
    plano (`marcar_hilo_fondo`) como máximo la mitad de ese cupo.

    Si se alcanzó el tope, espera (nunca más de ~1 s) en vez de provocar un 429 de Capital.com."""
    fondo = bool(getattr(_tl, "bg", False))
    tope_fondo = max(1, _MAX_PETICIONES_S // 2)
    while True:
        with _LOCK_RITMO:
            ahora = time.time()
            while _marcas_peticion and ahora - _marcas_peticion[0] >= 1.0:
                _marcas_peticion.pop(0)
            while _marcas_fondo and ahora - _marcas_fondo[0] >= 1.0:
                _marcas_fondo.pop(0)
            if len(_marcas_peticion) < _MAX_PETICIONES_S and (not fondo or len(_marcas_fondo) < tope_fondo):
                _marcas_peticion.append(ahora)
                if fondo:
                    _marcas_fondo.append(ahora)
                return
            if fondo and len(_marcas_fondo) >= tope_fondo:
                espera = 1.0 - (ahora - _marcas_fondo[0])
            else:
                espera = 1.0 - (ahora - _marcas_peticion[0])
        time.sleep(max(0.01, espera))


def _pedir(metodo: str, ruta: str, *, params=None, json=None, reintento=True):
    """Petición autenticada. Renueva sesión si hace falta y reintenta una vez ante 401 (solo si nadie la renovó ya)
    o ante 429 en lecturas GET. Devuelve el objeto requests.Response, o None si no hay conexión."""
    # Sin candado global durante la petición: antes cada llamada (~300-800 ms) bloqueaba a todas las
    # demás, y los refrescos en segundo plano retrasaban al rerun de la página. Solo la apertura de
    # sesión se serializa (en inicializar_mt5).
    if not inicializar_mt5():
        return None
    token_usado = _tokens["CST"]
    _limitar()
    try:
        r = _HTTP.request(metodo, f"{BASE}{ruta}", headers=_cabeceras(),
                          params=params, json=json, timeout=_TIMEOUT)
    except requests.exceptions.RequestException as e:
        print(f"[CAPITAL] Error de red en {metodo} {ruta}: {e}")
        return None
    # Token caducado/ inválido -> reautenticar una vez, salvo que otro hilo o proceso ya lo haya renovado
    if r.status_code == 401 and reintento:
        with _LOCK_SESION:
            if _tokens["CST"] == token_usado:
                _tokens["CST"] = ""
                _invalidar_archivo(token_usado)
                ok = _abrir_sesion(excluir_cst=token_usado)
            else:
                ok = True
        if ok:
            return _pedir(metodo, ruta, params=params, json=json, reintento=False)
    # Demasiado ritmo: una lectura se reintenta una vez tras una breve pausa
    if r.status_code == 429 and reintento and metodo.upper() == "GET":
        time.sleep(1.2)
        return _pedir(metodo, ruta, params=params, json=json, reintento=False)
    if r.status_code < 400:
        global _ultimo_uso
        _ultimo_uso = time.time()
        if _ultimo_uso - _ultimo_guardado > _INTERVALO_GUARDADO_S:
            _guardar_archivo()
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
}
_cache_epic: dict = {}


def _core_simbolo(name: str) -> str:
    """Núcleo comparable de un símbolo: sin '...' ni sufijos de bróker."""
    s = (name or "").upper().strip().replace("...", "").strip("#")
    if s.endswith("MICRO"):
        s = s[:-5]
    if "." in s:
        base, suf = s.rsplit(".", 1)
        if suf.isalnum() and 1 <= len(suf) <= 4:
            s = base
    return s


def _buscar_epic(termino: str):
    """Busca el epic de Capital por texto (GET /markets?searchTerm). Prefiere coincidencia
    exacta de epic; si no, el primer resultado. None si no hay nada."""
    if not termino:
        return None
    try:
        r = _pedir("GET", "/markets", params={"searchTerm": termino})
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
_TTL_FALLO_EPIC = 3 * 86400        # un símbolo sin epic se vuelve a buscar recién a los 3 días
_LOCK_EPICS = threading.Lock()
_epics_disco: dict = {}            # símbolo -> {"e": epic, "ok": bool, "t": epoch}
_epics_catalogo: set = set()


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


def _guardar_epics() -> None:
    try:
        os.makedirs(os.path.dirname(_RUTA_EPICS), exist_ok=True)
        tmp = _RUTA_EPICS + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_epics_disco, f)
        os.replace(tmp, _RUTA_EPICS)
    except Exception:
        pass


def resolver_simbolo(symbol: str) -> str:
    """Epic de Capital.com para un símbolo del proyecto: alias → catálogo/disco → ¿el núcleo es un epic? →
    búsqueda por texto. Los resultados (y los fallos, 3 días) se guardan en disco: tras el primer uso, resolver
    un símbolo ya conocido no hace ninguna llamada REST."""
    if not symbol:
        return symbol
    if symbol in _cache_epic:
        return _cache_epic[symbol]
    d = _epics_disco.get(symbol)
    if d and (d.get("ok") or time.time() - float(d.get("t", 0)) < _TTL_FALLO_EPIC):
        _cache_epic[symbol] = d["e"]
        return d["e"]
    core = _core_simbolo(symbol)
    epic = _ALIAS_EPIC.get(core)
    ok = True
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
                ok = epic is not None
                epic = epic or core
    _cache_epic[symbol] = epic
    with _LOCK_EPICS:
        _epics_disco[symbol] = {"e": epic, "ok": ok, "t": time.time()}
        _guardar_epics()
    return epic


_cargar_epics()


# ---------------------------------------------------------------------------
# Timeframes:  constante MT5 (int) o texto -> resolución de Capital.com
# ---------------------------------------------------------------------------
# Valores enteros de MetaTrader5.TIMEFRAME_* (para no importar el paquete MT5).
_TF_MT5_A_CAPITAL = {
    1: "MINUTE", 5: "MINUTE_5", 15: "MINUTE_15", 30: "MINUTE_30",
    16385: "HOUR", 16388: "HOUR_4", 16408: "DAY", 32769: "WEEK",
}
_RESOLUCIONES = {"MINUTE", "MINUTE_5", "MINUTE_15", "MINUTE_30", "HOUR", "HOUR_4", "DAY", "WEEK"}
TIMEFRAME_H1 = 16385   # por si algún caller usa backends.capital.TIMEFRAME_H1


def _resolucion(timeframe) -> str:
    if isinstance(timeframe, str) and timeframe.upper() in _RESOLUCIONES:
        return timeframe.upper()
    return _TF_MT5_A_CAPITAL.get(int(timeframe) if timeframe is not None else 16385, "HOUR")


def _seg_resolucion(resolucion: str) -> int:
    return {"MINUTE": 60, "MINUTE_5": 300, "MINUTE_15": 900, "MINUTE_30": 1800,
            "HOUR": 3600, "HOUR_4": 14400, "DAY": 86400, "WEEK": 604800}.get(resolucion, 3600)


def _epoch_utc(texto: str) -> int:
    """Convierte 'YYYY-MM-DDTHH:MM:SS(.mmm)' (UTC) a epoch en segundos."""
    if not texto:
        return 0
    t = texto.replace("Z", "")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return int(datetime.strptime(t, fmt).replace(tzinfo=timezone.utc).timestamp())
        except ValueError:
            continue
    return 0


# ---------------------------------------------------------------------------
# Cuenta
# ---------------------------------------------------------------------------
def _cuenta_preferida() -> dict:
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


def factor_lote(tipo: str) -> float:
    """Unidades de Capital por 1 lote en la interfaz: el Forex (CURRENCIES) usa el lote estándar
    de 100.000 unidades; el resto de instrumentos usa 1 unidad = 1 lote (como hasta ahora)."""
    return _UNID_POR_LOTE_FX if str(tipo).upper() == "CURRENCIES" else 1.0


def factor_lote_epic(epic: str) -> float:
    """Igual que factor_lote pero consultando el tipo del instrumento (cacheado)."""
    if epic not in _tipo_cache:
        r = _pedir("GET", f"/markets/{epic}")
        if r is not None and r.status_code == 200:
            _tipo_cache[epic] = (r.json().get("instrument", {}) or {}).get("type", "")
        else:
            return 1.0
    return factor_lote(_tipo_cache[epic])


def obtener_info_cuenta() -> dict:
    """Balance, equity y margen de la cuenta activa (equivalente a MT5). Cacheado ~2 s."""
    _ahora = time.time()
    _v = _cache_swr("cuenta", _TTL_CUENTA, obtener_info_cuenta)
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
    pl = float(bal.get("profitLoss", 0.0) or 0.0)          # P/G de posiciones abiertas
    disponible = float(bal.get("available", 0.0) or 0.0)
    _res = {
        "login": c.get("accountId", ""),
        "nombre": c.get("accountName", ""),
        "servidor": "Capital.com (demo)" if _ES_DEMO else "Capital.com",
        "tipo": "Demo" if _ES_DEMO else "Real",
        "balance": balance,
        "equity": equity,
        "profit": pl,
        "margin": max(0.0, equity - disponible),
        "margin_free": disponible,
        "margin_level": (100.0 * equity / (equity - disponible))
                        if (equity - disponible) > 0 else 0.0,
        "credit": 0.0,
        "leverage": 0,
        "currency": c.get("currency", "USD"),
        "deposito": float(bal.get("deposit", 0.0) or 0.0),   # depósito de la cuenta (Capital /accounts)
    }
    _cache_lectura["cuenta"] = (_ahora, _res)
    return _res


# ---------------------------------------------------------------------------
# Posiciones
# ---------------------------------------------------------------------------
def obtener_posiciones() -> list:
    """Posiciones abiertas (para la 'Cartera'). Cacheado ~2 s."""
    _ahora = time.time()
    _v = _cache_swr("posiciones", _TTL_POSICIONES, obtener_posiciones)
    if _v is not None:
        return _v
    r = _pedir("GET", "/positions")
    if r is None or r.status_code != 200:
        return []
    salida = []
    for item in r.json().get("positions", []):
        p = item.get("position", {}) or {}
        m = item.get("market", {}) or {}
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


def _buscar_posicion(dealId) -> dict:
    """Devuelve el item {position, market} de una posición por su dealId."""
    r = _pedir("GET", f"/positions/{dealId}")
    if r is not None and r.status_code == 200:
        return r.json()
    # Respaldo: recorrer todas
    r = _pedir("GET", "/positions")
    if r is None or r.status_code != 200:
        return {}
    for item in r.json().get("positions", []):
        if str(item.get("position", {}).get("dealId")) == str(dealId):
            return item
    return {}


def especs_posicion(ticket) -> dict:
    """Datos del contrato de una posición para el panel de TP/SL de la Cartera.
    NOTA: `k` (valor por unidad de precio) es aproximado = contractSize, asumiendo
    instrumento cotizado en la moneda de la cuenta (USD). Afinar si se opera un
    instrumento con otra divisa de cotización."""
    item = _buscar_posicion(ticket)
    if not item:
        return {}
    p = item.get("position", {}) or {}
    epic = item.get("market", {}).get("epic", "")
    d = get_mercado(epic)
    if not d:
        return {}
    snap = d.get("snapshot", {}) or {}
    reglas = d.get("dealingRules", {}) or {}
    digitos = int(snap.get("decimalPlacesFactor", 2) or 2)
    point = 10 ** (-digitos)
    bid = float(snap.get("bid", 0.0) or 0.0)
    ask = float(snap.get("offer", 0.0) or 0.0)
    contract = float(p.get("contractSize", 1.0) or 1.0)
    snap_tipo = (d.get("instrument", {}) or {}).get("type", "")
    # Distancia mínima de stop: Capital la da en % -> la pasamos a "puntos".
    md = reglas.get("minStopOrProfitDistance", {}) or {}
    if (md.get("unit") == "PERCENTAGE") and bid:
        dist_precio = bid * float(md.get("value", 0.0) or 0.0) / 100.0
        stops_level = int(dist_precio / point) if point else 0
    else:
        stops_level = int(float(md.get("value", 0.0) or 0.0) / point) if point else 0
    return {
        "k": contract * factor_lote(snap_tipo),
        "digitos": digitos,
        "point": float(point),
        "stops_level": stops_level,
        "bid": bid,
        "ask": ask,
        "srv_now": float(time.time()),
        "precio_apertura": float(p.get("level", 0.0) or 0.0),
        "tipo": "Compra" if p.get("direction", "").upper() == "BUY" else "Venta",
        "volumen": float(p.get("size", 0.0) or 0.0) / factor_lote(snap_tipo),
    }


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
        tipo_tx = str(t.get("transactionType", "")).upper()
        if "TRADE" not in tipo_tx and "DEAL" not in tipo_tx:
            continue
        # P/G realizado: campos posibles según versión de la API.
        pg = (t.get("profitAndLoss") or t.get("pnl") or t.get("size") or 0)
        try:
            pg = float(str(pg).replace(t.get("currency", "") or "", "").strip() or 0)
        except ValueError:
            pg = 0.0
        salida.append({
            "ticket": t.get("reference", ""),
            "deal_id": t.get("dealId", ""),          # id de la posición (para detalle_cierre)
            "symbol": t.get("instrumentName", ""),
            "tipo": t.get("transactionType", ""),
            "volumen": 0.0,
            "precio_cierre": 0.0,
            "pg": pg,
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
_LOCK_CIERRES = threading.Lock()


def _cargar_cierres() -> None:
    try:
        with open(_RUTA_CIERRES, "r", encoding="utf-8") as f:
            _cierres.update(json.load(f))
    except Exception:
        pass


def _actividad(deal_id: str, desde_ts: float, hasta_ts: float) -> list:
    """Actividades de una posición dentro de una ventana (máx. 24 h) en epoch UTC."""
    fmt = "%Y-%m-%dT%H:%M:%S"
    r = _pedir("GET", "/history/activity", params={
        "from": datetime.fromtimestamp(desde_ts, timezone.utc).strftime(fmt),
        "to": datetime.fromtimestamp(hasta_ts, timezone.utc).strftime(fmt),
        "dealId": deal_id, "detailed": "true"})
    if r is None or r.status_code != 200:
        return []
    return [a for a in r.json().get("activities", []) if a.get("dealId") == deal_id]


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
    res = {"epic": epic, "tipo": tipo,
           "volumen": float(d.get("size", 0.0) or 0.0) / factor_lote_epic(epic),
           "entrada": float(d.get("openPrice", 0.0) or 0.0), "salida": float(d.get("level", 0.0) or 0.0),
           "hora_in": int(hora_in)}
    with _LOCK_CIERRES:
        _cierres[deal_id] = res
        try:
            tmp = _RUTA_CIERRES + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(_cierres, f)
            os.replace(tmp, _RUTA_CIERRES)
        except Exception:
            pass
    return res


_cargar_cierres()


# ---------------------------------------------------------------------------
# Precios e histórico de velas
# ---------------------------------------------------------------------------
def obtener_precio_actual(symbol: str) -> dict:
    """Bid/Ask del instrumento (snapshot del mercado). Cacheado ~3 s por epic."""
    epic = resolver_simbolo(symbol)
    _ahora = time.time()
    _v = _cache_swr(f"precio:{epic}", _TTL_PRECIO, obtener_precio_actual, symbol)
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
    _res = {
        "symbol": epic,
        "bid": bid,
        "ask": ask,
        "last": bid or ask,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    _cache_lectura[f"precio:{epic}"] = (_ahora, _res)
    return _res


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
        r = _pedir("GET", "/markets", params={"epics": ",".join(lote)})
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


def _velas_crudas(epic: str, resolucion: str, maximo: int = None,
                  desde: str = None, hasta: str = None) -> list:
    params = {"resolution": resolucion}
    if maximo:
        params["max"] = min(int(maximo), _MAX_VELAS_CAPITAL)
    if desde:
        params["from"] = desde
    if hasta:
        params["to"] = hasta
    r = _pedir("GET", f"/prices/{epic}", params=params)
    if r is None or r.status_code != 200:
        return []
    return r.json().get("prices", [])


def _mid(precio: dict) -> float:
    """Precio BID de una pieza open/close/high/low de la vela (como MT5 y como los ticks en vivo:
    así la vela que se mueve con los ticks y la que llega por REST no difieren en el spread)."""
    b = precio.get("bid"); a = precio.get("ask")
    if b is not None:
        return float(b)
    return float(a if a is not None else 0.0)


_TIMEFRAME_MN1 = 49153   # Capital.com no tiene resolución mensual: el mes se arma con velas semanales y diarias


def _punto_de(epic: str) -> float:
    """Tamaño del punto (10 elevado a menos los decimales) del instrumento, según `decimalPlacesFactor`; 0.0 si no se conoce."""
    try:
        snap = (get_mercado(epic) or {}).get("snapshot", {}) or {}
        return 10 ** (-int(snap.get("decimalPlacesFactor", 2) or 2))
    except Exception:
        return 0.0


def _spread_puntos(pieza: dict, punto: float) -> float:
    """Spread de una vela en puntos: (ask - bid) del cierre dividido por el punto. 0.0 si la vela no trae ambos precios.

    Capital.com entrega bid y ask en cada vela, y el backtest/replay lo usa como el spread histórico que daba MT5."""
    b = pieza.get("bid")
    a = pieza.get("ask")
    if b is None or a is None or not punto:
        return 0.0
    return float(max(0.0, round((float(a) - float(b)) / punto)))


def _filas_velas(velas: list, punto: float) -> list:
    """Convierte las velas crudas de Capital.com en filas time/open/high/low/close/tick_volume/spread (precios BID)."""
    return [{
        "time": _epoch_utc(v.get("snapshotTimeUTC") or v.get("snapshotTime")),
        "open": _mid(v.get("openPrice", {})),
        "high": _mid(v.get("highPrice", {})),
        "low": _mid(v.get("lowPrice", {})),
        "close": _mid(v.get("closePrice", {})),
        "tick_volume": v.get("lastTradedVolume", 0),
        "spread": _spread_puntos(v.get("closePrice", {}), punto),
    } for v in velas]


def _agrupar_meses(semanales: list, diarias: list) -> list:
    """Arma velas mensuales (inicio de mes UTC) a partir de filas semanales y diarias, de la más antigua a la más reciente.

    Cada mes posterior al primero cubierto por las velas diarias se calcula con ellas (exacto); ese primer mes (incompleto en las
    diarias) y los anteriores, con las semanales (cada semana cuenta en el mes en que empieza, así que el borde puede variar unos días). Apertura = primera vela,
    cierre = última, máximo y mínimo = extremos, volumen = suma y spread = el de la última vela."""
    def mes(t):
        g = time.gmtime(t)
        return (g.tm_year, g.tm_mon)

    def agrupar(filas):
        grupos: dict = {}
        for f in sorted(filas, key=lambda x: x["time"]):
            grupos.setdefault(mes(f["time"]), []).append(f)
        return grupos
    dias = agrupar(diarias)
    primer_mes = min(dias) if dias else None
    sem = agrupar(semanales)
    meses = {k: v for k, v in sem.items() if primer_mes is None or k <= primer_mes}   # el primer mes de las diarias está incompleto
    meses.update({k: v for k, v in dias.items() if k != primer_mes or k not in meses})
    out = []
    for (anio, m) in sorted(meses):
        g = meses[(anio, m)]
        out.append({
            "time": calendar.timegm((anio, m, 1, 0, 0, 0)),
            "open": g[0]["open"], "close": g[-1]["close"],
            "high": max(x["high"] for x in g), "low": min(x["low"] for x in g),
            "tick_volume": sum(x["tick_volume"] for x in g), "spread": g[-1]["spread"],
        })
    return out


def _datos_mensuales(epic: str, n_meses: int) -> list:
    """Filas mensuales de los últimos `n_meses`: pide a Capital.com las semanales y diarias necesarias y las agrupa por mes."""
    punto = _punto_de(epic)
    dias = _filas_velas(_velas_crudas(epic, "DAY", maximo=min(_MAX_VELAS_CAPITAL, n_meses * 31 + 5)), punto)
    semanas = _filas_velas(_velas_crudas(epic, "WEEK", maximo=min(_MAX_VELAS_CAPITAL, int(n_meses * 4.4) + 6)), punto)
    return _agrupar_meses(semanas, dias)[-n_meses:]


def obtener_datos_historicos(symbol: str, timeframe=TIMEFRAME_H1, n_velas: int = 100) -> pd.DataFrame:
    """OHLCV histórico como DataFrame indexado por tiempo (equivalente a MT5), con la columna `spread` en puntos.

    Para la temporalidad mensual (la constante MN1 de MT5) Capital.com no ofrece resolución propia, así que se agrupan
    velas semanales y diarias (ver `_agrupar_meses`)."""
    epic = resolver_simbolo(symbol)
    if timeframe == _TIMEFRAME_MN1:
        filas = _datos_mensuales(epic, int(n_velas))
    else:
        filas = _filas_velas(_velas_crudas(epic, _resolucion(timeframe), maximo=int(n_velas)), _punto_de(epic))
    if not filas:
        return pd.DataFrame()
    df = pd.DataFrame(filas)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df.set_index("time")


_PAGINAS_MAX = 80


def _texto_utc(ts: float) -> str:
    """Epoch -> 'YYYY-MM-DDTHH:MM:SS' (UTC), el formato de `from`/`to` de /prices."""
    return datetime.fromtimestamp(max(float(ts), 86400.0), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def obtener_datos_anteriores(symbol: str, timeframe, antes_de: float, cantidad: int) -> pd.DataFrame:
    """Hasta `cantidad` velas ANTERIORES al instante `antes_de` (epoch, excluido), con el mismo formato que `obtener_datos_historicos`.

    Capital.com entrega como máximo 1000 velas por petición, así que el historial más largo se pide por tramos hacia atrás: cada
    petición usa una ventana de tiempo `from`–`to` que debe contener menos de 1000 velas (así el tope `max` nunca decide qué velas
    llegan). El tamaño de la ventana se adapta a la densidad observada (en instrumentos que cierran de noche entra menos de una
    vela por hueco), y si una ventana llena el tope se parte a la mitad y se repite. Termina al juntar `cantidad` velas, tras dos
    ventanas seguidas sin datos (fin del historial) o a las `_PAGINAS_MAX` peticiones. DataFrame vacío si no hay nada más antiguo.
    No admite la temporalidad mensual (esa se arma aparte)."""
    epic = resolver_simbolo(symbol)
    res = _resolucion(timeframe)
    seg = _seg_resolucion(res)
    punto = _punto_de(epic)
    huecos = int(_MAX_VELAS_CAPITAL * 0.9)       # velas que cabe esperar en una ventana
    ventana = huecos * seg
    fin = float(antes_de) - 1
    filas: dict = {}
    vacias = 0
    for _ in range(_PAGINAS_MAX):
        if len(filas) >= cantidad or vacias >= 2 or fin < 86400.0:
            break
        ini = fin - ventana
        crudas = _filas_velas(_velas_crudas(epic, res, maximo=_MAX_VELAS_CAPITAL,
                                            desde=_texto_utc(ini), hasta=_texto_utc(fin)), punto)
        crudas = [f for f in crudas if f["time"] <= fin]
        if len(crudas) >= _MAX_VELAS_CAPITAL:   # ventana llena: pudo quedar un hueco, se repite con una más corta
            ventana = max(seg * 10, ventana // 2)
            continue
        if not crudas:
            vacias += 1
        else:
            vacias = 0
            for f in crudas:
                filas[f["time"]] = f
            densidad = len(crudas) / max(1.0, ventana / seg)
            ventana = int(min(max(huecos / max(densidad, 0.02), 100), 6000)) * seg
        fin = ini - 1
    if not filas:
        return pd.DataFrame()
    df = pd.DataFrame([filas[t] for t in sorted(filas)][-int(cantidad):])
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df.set_index("time")


def obtener_velas_rango(symbol: str, ts_desde: float, ts_hasta: float) -> list:
    """Velas OHLC que cubren [ts_desde, ts_hasta] (epoch), para el mini-gráfico del
    Trading Journal. Elige la resolución según la duración (~40-120 velas)."""
    # Blindaje: timestamps inválidos (<=0) darían un inicio negativo y datetime.fromtimestamp
    # revienta en Windows (OSError 22). Sin rango útil no se dibuja nada.
    if not ts_hasta or float(ts_hasta) <= 0:
        return []
    dur = max(60.0, float(ts_hasta) - float(ts_desde))
    pad = dur * 0.35 + 300
    d0, d1 = float(ts_desde) - pad, float(ts_hasta) + pad
    d0 = max(d0, 86400.0)      # nunca antes de 1970 (evita OSError en Windows)
    objetivo = (d1 - d0) / 60.0
    escala = ["MINUTE", "MINUTE_5", "MINUTE_15", "HOUR", "HOUR_4", "DAY"]
    res = escala[0]
    for r_ in escala:
        res = r_
        if _seg_resolucion(r_) >= objetivo:
            break
    epic = resolver_simbolo(symbol)
    desde = datetime.fromtimestamp(d0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    hasta = datetime.fromtimestamp(d1, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    velas = _velas_crudas(epic, res, desde=desde, hasta=hasta, maximo=1000)
    out = []
    for v in velas:
        t = _epoch_utc(v.get("snapshotTimeUTC") or v.get("snapshotTime"))
        out.append({"t": t, "o": _mid(v.get("openPrice", {})), "h": _mid(v.get("highPrice", {})),
                    "l": _mid(v.get("lowPrice", {})), "c": _mid(v.get("closePrice", {}))})
    return out


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


def ejecutar_orden_mercado(symbol: str, tipo: str, volumen: float, sl: float = 0.0, tp: float = 0.0) -> dict:
    """Orden a mercado (BUY/SELL). Abre una posición en Capital.com."""
    epic = resolver_simbolo(symbol)
    cuerpo = {"epic": epic, "direction": tipo.upper(), "size": round(float(volumen) * factor_lote_epic(epic), 6)}
    if sl and sl > 0:
        cuerpo["stopLevel"] = float(sl)
    if tp and tp > 0:
        cuerpo["profitLevel"] = float(tp)
    with _ORDER_LOCK:
        r = _pedir("POST", "/positions", json=cuerpo)
    if r is None:
        return {"error": "Sin conexión con Capital.com"}
    if r.status_code >= 400:
        return {"error": f"Fallo al enviar orden (HTTP {r.status_code}): {r.text}"}
    conf = _confirmar(r.json().get("dealReference", ""))
    if "error" in conf:
        return conf
    # Trading Journal: guarda el plan (entrada + SL + TP) ligado a la posición.
    if (sl and sl > 0) or (tp and tp > 0):
        try:
            from herramientas import almacen_diario
            almacen_diario.guardar_plan(conf["dealId"], conf.get("level") or 0.0, sl, tp,
                                        tipo.upper(), epic, float(volumen))
        except Exception:
            pass
    _invalidar()
    return {"status": "success", "order": conf["dealId"], "price": conf.get("level") or 0.0,
            "volume": float(volumen), "symbol": epic}


def colocar_orden_pendiente(symbol: str, tipo: str, volumen: float, precio: float,
                            sl: float = 0.0, tp: float = 0.0,
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
    ref = precio_actual["ask"] if compra else precio_actual["bid"]
    if compra:
        tipo_orden, nombre = ("LIMIT", "Buy Limit") if precio < ref else ("STOP", "Buy Stop")
    else:
        tipo_orden, nombre = ("LIMIT", "Sell Limit") if precio > ref else ("STOP", "Sell Stop")
    cuerpo = {"epic": epic, "direction": tipo.upper(), "size": round(float(volumen) * factor_lote_epic(epic), 6),
              "level": float(precio), "type": tipo_orden}
    if sl and sl > 0:
        cuerpo["stopLevel"] = float(sl)
    if tp and tp > 0:
        cuerpo["profitLevel"] = float(tp)
    if not hasta_cancelar:   # solo hoy (DAY): caduca al final del día UTC
        fin = datetime.now(timezone.utc).replace(hour=23, minute=59, second=0, microsecond=0)
        cuerpo["goodTillDate"] = fin.strftime("%Y-%m-%dT%H:%M:%S")
    with _ORDER_LOCK:
        r = _pedir("POST", "/workingorders", json=cuerpo)
    if r is None:
        return {"error": "Sin conexión con Capital.com"}
    if r.status_code >= 400:
        return {"error": f"Fallo al colocar la orden pendiente (HTTP {r.status_code}): {r.text}"}
    conf = _confirmar(r.json().get("dealReference", ""))
    if "error" in conf:
        return conf
    _invalidar()
    return {"status": "success", "order": conf["dealId"], "price": float(precio),
            "volume": float(volumen), "symbol": epic, "tipo": nombre}


def cerrar_posicion(ticket) -> dict:
    """Cierra una posición abierta por su dealId."""
    item = _buscar_posicion(ticket)
    p = item.get("position", {}) if item else {}
    symbol = item.get("market", {}).get("epic", "") if item else ""
    profit = float(p.get("upl", 0.0) or 0.0)
    with _ORDER_LOCK:
        r = _pedir("DELETE", f"/positions/{ticket}")
    if r is None:
        return {"error": "Sin conexión con Capital.com"}
    if r.status_code >= 400:
        return {"error": f"Fallo al cerrar (HTTP {r.status_code}): {r.text}"}
    conf = _confirmar(r.json().get("dealReference", ""))
    if "error" in conf:
        return conf
    _invalidar()
    return {"status": "success", "profit": profit, "symbol": symbol}


def _niveles_actuales(ticket) -> tuple:
    """(stopLevel, profitLevel) vigentes de una posición (0.0 = sin nivel)."""
    item = _buscar_posicion(ticket)
    p = item.get("position", {}) if item else {}
    return float(p.get("stopLevel", 0.0) or 0.0), float(p.get("profitLevel", 0.0) or 0.0)


def modificar_sltp(ticket, sl=None, tp=None) -> dict:
    """Cambia el Stop Loss / Take Profit de una posición abierta.
    None = deja el valor actual · 0 = QUITA ese nivel. Capital reemplaza ambos niveles en cada
    PUT (lo que no se envía se elimina), así que siempre se mandan los dos ya combinados."""
    if sl is None and tp is None:
        return {"error": "Nada que modificar"}
    sl_act, tp_act = _niveles_actuales(ticket)
    sl_nuevo = sl_act if sl is None else float(sl)
    tp_nuevo = tp_act if tp is None else float(tp)
    cuerpo = {}
    if sl_nuevo > 0:
        cuerpo["stopLevel"] = sl_nuevo
    if tp_nuevo > 0:
        cuerpo["profitLevel"] = tp_nuevo
    with _ORDER_LOCK:
        r = _pedir("PUT", f"/positions/{ticket}", json=cuerpo)
    if r is None:
        return {"error": "Sin conexión con Capital.com"}
    if r.status_code >= 400:
        return {"error": f"No se pudo modificar (HTTP {r.status_code}): {r.text}"}
    conf = _confirmar(r.json().get("dealReference", ""))
    if "error" in conf:
        return conf
    _invalidar()
    return {"status": "success", "ticket": ticket,
            "sl": cuerpo.get("stopLevel", 0.0), "tp": cuerpo.get("profitLevel", 0.0)}


_NOMBRE_PENDIENTE = {"LIMIT": "Limit", "STOP": "Stop"}


def modificar_orden(ticket, precio=None, sl=None, tp=None,
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
    sl_n = float(sl) if sl is not None else float(actual.get("stopLevel", 0.0) or 0.0)
    tp_n = float(tp) if tp is not None else float(actual.get("profitLevel", 0.0) or 0.0)
    if sl_n > 0:
        cuerpo["stopLevel"] = sl_n
    if tp_n > 0:
        cuerpo["profitLevel"] = tp_n
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
    with _ORDER_LOCK:
        r = _pedir("PUT", f"/workingorders/{ticket}", json=cuerpo)
    if r is None:
        return {"error": "Sin conexión con Capital.com"}
    if r.status_code >= 400:
        return {"error": f"No se pudo modificar la orden (HTTP {r.status_code}): {r.text}"}
    conf = _confirmar(r.json().get("dealReference", ""))
    if "error" in conf:
        return conf
    _invalidar()
    return {"status": "success", "ticket": ticket, "price": cuerpo.get("level", 0.0),
            "sl": cuerpo.get("stopLevel", 0.0), "tp": cuerpo.get("profitLevel", 0.0)}


def eliminar_orden(ticket) -> dict:
    """Cancela una orden PENDIENTE (working order)."""
    with _ORDER_LOCK:
        r = _pedir("DELETE", f"/workingorders/{ticket}")
    if r is None:
        return {"error": "Sin conexión con Capital.com"}
    if r.status_code >= 400:
        return {"error": f"No se pudo cancelar la orden (HTTP {r.status_code}): {r.text}"}
    conf = _confirmar(r.json().get("dealReference", ""))
    if "error" in conf:
        return conf
    _invalidar()
    return {"status": "success", "ticket": ticket, "tipo": "", "symbol": ""}


# ---------------------------------------------------------------------------
# Profundidad de mercado (DOM): no disponible por REST en Capital.com
# ---------------------------------------------------------------------------
def obtener_dom(symbol: str, niveles: int = 8) -> dict:
    return {"ask": [], "bid": [], "disponible": False,
            "motivo": "Capital.com no entrega libro de órdenes (DOM) por su API REST."}
