"""Conexión con MetaTrader 5, candado, símbolos y utilidades — SOLO LECTURA.

NOMBRE DEL ARCHIVO: fuentes/mt5_fuente.py  (en singular, igual que yfinance_fuente.py e
investing_fuente.py y como lo importa herramientas/mt5_tools.py: `from fuentes import mt5_fuente`).

Estrategia de conexión (la de tu mt5_bridge.py, que ya funciona con tu terminal):
  * NUNCA se llama a initialize() sin ruta (en tu equipo da "IPC timeout" y cuelga hasta 60 s).
  * Se prueban rutas candidatas, en este orden: MT5_PATH del .env -> terminal64.exe que esté
    abierto ahora -> carpetas típicas de instalación (máximo 3 intentos).
  * Máximo 10 s por intento y, si no conecta, espera 15 s antes de reintentar. Durante esa
    espera las llamadas fallan al instante (no se quedan esperando el candado).
  * Se usa la sesión que ya está iniciada en el terminal. Solo si MT5_LOGIN, MT5_PASSWORD y
    MT5_SERVER están los tres en el .env se hace login explícito.

CANDADO: la API de MT5 no es segura entre hilos. Si existe el bridge del dashboard
(tools.mt5_bridge, o el módulo indicado en MT5_BRIDGE_MODULO) se comparte su MT5_LOCK; si no,
se usa uno propio. Se decide UNA vez, al importar este módulo (nunca cambia a mitad de camino).
Un candado no cruza procesos: si dashboard y agente corren en procesos distintos, MT5 los
atiende a ambos, pero no se excluyen entre sí.

SEGURIDAD: los datos se leen a través de _SoloLectura, que solo deja pasar consultas. Cualquier
otra función (order_send, order_check, login, initialize, shutdown...) queda bloqueada.
Nunca se llama a shutdown().

DATOS POR USUARIO: MT5 trabaja con UNA cuenta por terminal. Para no entregar los datos de una
persona a otra:
  * exigir_cuenta_de(mt5, login_esperado) compara la cuenta abierta con la del usuario.
  * Opcional, para instalaciones de un solo usuario: MT5_LOGIN_ESPERADO (y MT5_SERVER_ESPERADO)
    en el .env; _exigir_cuenta() lo verifica.
  * datos_cuenta_seguros() entrega el resumen de cuenta con el login enmascarado y sin nombre.
  * El usuario debe venir de la sesión del dashboard, NUNCA de un argumento que decida el LLM.

Las horas de MT5 son del SERVIDOR del broker, no tu hora local (ver offset_servidor_horas).
"""
from __future__ import annotations

import glob
import importlib
import os
import subprocess
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator, NoReturn

try:
    import config  # noqa: F401
except ImportError:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

_TIMEOUT_MS = 10_000
_REINTENTO_S = 15
_TTL_SIMBOLOS_S = 600
_TTL_RUTAS_S = 300
_TTL_OFFSET_S = 300
_MAX_RUTAS = 3

TIMEFRAMES = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 16385,
    "H4": 16388,
    "D1": 16408,
    "W1": 32769,
    "MN1": 49153,
}

_FUNCIONES_PERMITIDAS = frozenset(
    {
        "last_error", "version", "terminal_info", "account_info",
        "symbols_get", "symbols_total", "symbol_info", "symbol_info_tick", "symbol_select",
        "copy_rates_from_pos", "copy_rates_range",
        "positions_get", "positions_total", "orders_get", "orders_total",
        "history_deals_get", "history_deals_total", "history_orders_get", "history_orders_total",
        "order_calc_margin", "order_calc_profit",
    }
)


class ErrorMT5(Exception):
    """Fallo de la fuente MT5."""


class OperacionNoPermitida(ErrorMT5, AttributeError):
    """Se intentó usar una función de MT5 vetada (solo lectura)."""


class _SoloLectura:
    """Envuelve el módulo MetaTrader5 y solo deja pasar consultas."""

    def __init__(self, modulo: Any) -> None:
        object.__setattr__(self, "_modulo", modulo)

    def __getattr__(self, nombre: str) -> Any:
        if nombre.startswith("__"):
            raise AttributeError(nombre)
        if nombre in _FUNCIONES_PERMITIDAS or nombre.isupper():
            return getattr(self._modulo, nombre)
        raise OperacionNoPermitida(f"Operación no permitida: '{nombre}'. El agente es de solo lectura.")

    def __setattr__(self, nombre: str, valor: Any) -> None:
        raise OperacionNoPermitida("El módulo MT5 es de solo lectura.")


_LOCK_PROPIO = threading.RLock()


def _resolver_lock_compartido() -> Any:
    ruta = os.getenv("MT5_BRIDGE_MODULO", "tools.mt5_bridge").strip() or "tools.mt5_bridge"
    try:
        return importlib.import_module(ruta).MT5_LOCK
    except Exception:
        return None


_LOCK_COMPARTIDO: Any = _resolver_lock_compartido()


def _lock() -> Any:
    return _LOCK_COMPARTIDO if _LOCK_COMPARTIDO is not None else _LOCK_PROPIO


def _terminal_en_ejecucion() -> list[str]:
    try:
        salida = subprocess.run(
            [
                "powershell", "-NoProfile", "-Command",
                "Get-Process terminal64 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Path",
            ],
            capture_output=True, text=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout
        return [l.strip() for l in salida.splitlines() if l.strip().lower().endswith("terminal64.exe")]
    except Exception:
        return []


_rutas_cache: tuple[float, list[str]] | None = None


def rutas_candidatas(refrescar: bool = False) -> list[str]:
    global _rutas_cache
    ahora = time.monotonic()
    if _rutas_cache is not None and not refrescar and ahora - _rutas_cache[0] < _TTL_RUTAS_S:
        return list(_rutas_cache[1])

    rutas: list[str] = []
    en_env = os.getenv("MT5_PATH", "").strip().strip('"')
    if en_env and os.path.isfile(en_env):
        rutas.append(en_env)
    rutas += _terminal_en_ejecucion()
    for base in (
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        os.path.expandvars(r"%APPDATA%\MetaQuotes\Terminal"),
    ):
        rutas += glob.glob(os.path.join(base, "*", "terminal64.exe"))
    vistas: set[str] = set()
    unicas: list[str] = []
    for r in rutas:
        k = os.path.normcase(os.path.abspath(r))
        if k not in vistas and os.path.isfile(r):
            vistas.add(k)
            unicas.append(r)
    if unicas:
        _rutas_cache = (ahora, unicas)
    return unicas


_raw: Any = None
_proxy: _SoloLectura | None = None
_ultimo_fallo = 0.0
_ultimo_error = ""
_ruta_conectada: str | None = None


def _modulo() -> Any:
    global _raw, _proxy
    if _raw is None:
        try:
            _raw = importlib.import_module("MetaTrader5")
        except ImportError as e:
            raise ErrorMT5("Falta la librería MetaTrader5: pip install -U MetaTrader5") from e
        _proxy = _SoloLectura(_raw)
    return _raw


def _fallar(mensaje: str) -> NoReturn:
    global _ultimo_fallo, _ultimo_error
    _ultimo_fallo = time.time()
    _ultimo_error = mensaje
    raise ErrorMT5(mensaje)


def _espera_restante() -> float:
    if not _ultimo_error:
        return 0.0
    return max(0.0, _REINTENTO_S - (time.time() - _ultimo_fallo))


def _conectar(raw: Any) -> None:
    global _ruta_conectada, _ultimo_error
    rutas = rutas_candidatas()
    if not rutas:
        _fallar("No se encontró ningún terminal64.exe de MT5.")

    errores: list[str] = []
    for ruta in rutas[:_MAX_RUTAS]:
        if raw.initialize(path=ruta, timeout=_TIMEOUT_MS):
            _ruta_conectada = ruta
            break
        errores.append(f"{ruta} → {raw.last_error()}")
    else:
        _fallar("No se pudo conectar con MT5: " + " | ".join(errores))

    _ultimo_error = ""


def asegurar_conexion() -> _SoloLectura:
    raw = _modulo()
    if raw.terminal_info() is None:
        espera = _espera_restante()
        if espera > 0:
            raise ErrorMT5(f"{_ultimo_error} (reintento en {espera:.0f} s)")
        _conectar(raw)
    if _proxy is None:
        raise ErrorMT5("Módulo MT5 no inicializado.")
    return _proxy


@contextmanager
def _sesion() -> Iterator[_SoloLectura]:
    lock = _lock()
    if _espera_restante() > 0:
        if not lock.acquire(blocking=False):
            raise ErrorMT5(f"{_ultimo_error} (reintento en {_espera_restante():.0f} s)")
    else:
        lock.acquire()
    try:
        yield asegurar_conexion()
    finally:
        lock.release()


def _num(v: Any, dec: int = 5) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return round(f, dec)


def _nivel(v: Any) -> float | None:
    return _num(v) if v else None


def _hora_utc(ts: Any, mt5: Any) -> str:
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S") + " UTC"


def _fecha_utc(texto: str, campo: str) -> datetime:
    try:
        return datetime.strptime(texto, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise ErrorMT5(f"'{campo}' debe tener formato AAAA-MM-DD.") from None


def _como_tupla(mt5: Any, resultado: Any, accion: str) -> Any:
    if resultado is None:
        err = mt5.last_error()
        if err and err[0] != getattr(mt5, "RES_S_OK", 1):
            raise ErrorMT5(f"MT5 falló al {accion}: {err}")
        return ()
    return resultado


_ALIAS = {
    "GOLD": ["XAUUSD", "GOLD"],
    "XAUUSD": ["XAUUSD", "GOLD"],
    "US500": ["US500", "SPX500", "US500CASH"],
    "EURUSD": ["EURUSD", "EURUSDmicro"],
}


def _resolver(mt5: Any, texto: str) -> str:
    bruto = (texto or "").strip().upper()
    if not bruto:
        raise ErrorMT5("Falta el símbolo.")
    info = mt5.symbol_info(bruto)
    if info is not None:
        return bruto
    for alias in _ALIAS.get(bruto, []):
        if mt5.symbol_info(alias) is not None:
            return alias
    return bruto


@contextmanager
def _simbolo_temporal(mt5: Any, simbolo: str) -> Iterator[Any]:
    info = mt5.symbol_info(simbolo)
    if info is None:
        raise ErrorMT5(f"El símbolo '{simbolo}' no existe en MT5.")
    estaba_visible = bool(info.visible)
    if not estaba_visible:
        mt5.symbol_select(simbolo, True)
    try:
        yield info
    finally:
        if not estaba_visible:
            try:
                mt5.symbol_select(simbolo, False)
            except Exception:
                pass


# ──────────────────────────────────────────────────────────────
# Funciones Públicas requeridas por mt5_tools.py
# ──────────────────────────────────────────────────────────────

def cuenta() -> dict[str, Any]:
    with _sesion() as mt5:
        c = mt5.account_info()
        if c is None:
            raise ErrorMT5("No hay una cuenta iniciada en MT5.")
        return {
            "fuente": "MetaTrader 5",
            "tipo": "DEMO" if getattr(c, "trade_mode", 0) == 0 else "REAL",
            "moneda": getattr(c, "currency", "USD"),
            "balance": _num(getattr(c, "balance", None), 2),
            "equidad": _num(getattr(c, "equity", None), 2),
            "beneficio_flotante": _num(getattr(c, "profit", None), 2),
            "margen_usado": _num(getattr(c, "margin", None), 2),
            "margen_libre": _num(getattr(c, "margin_free", None), 2),
            "nivel_margen_pct": _num(getattr(c, "margin_level", None), 2),
            "apalancamiento": getattr(c, "leverage", None),
            "consultado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }


def posiciones(simbolo: str | None = None) -> dict[str, Any]:
    with _sesion() as mt5:
        sym = _resolver(mt5, simbolo) if simbolo else None
        pos_tuple = mt5.positions_get(symbol=sym) if sym else mt5.positions_get()
        pos_tuple = _como_tupla(mt5, pos_tuple, "obtener posiciones")

        resultado = []
        for p in pos_tuple:
            resultado.append({
                "ticket": getattr(p, "ticket", None),
                "simbolo": getattr(p, "symbol", None),
                "tipo": "COMPRA" if getattr(p, "type", 0) == 0 else "VENTA",
                "lotes": _num(getattr(p, "volume", None)),
                "precio_apertura": _num(getattr(p, "price_open", None)),
                "precio_actual": _num(getattr(p, "price_current", None)),
                "sl": _nivel(getattr(p, "sl", None)),
                "tp": _nivel(getattr(p, "tp", None)),
                "beneficio": _num(getattr(p, "profit", None)),
                "swap": _num(getattr(p, "swap", None)),
            })

        return {
            "fuente": "MetaTrader 5",
            "total_posiciones": len(resultado),
            "posiciones": resultado,
            "consultado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }


def ordenes_pendientes(simbolo: str | None = None) -> dict[str, Any]:
    with _sesion() as mt5:
        sym = _resolver(mt5, simbolo) if simbolo else None
        ordenes = mt5.orders_get(symbol=sym) if sym else mt5.orders_get()
        ordenes = _como_tupla(mt5, ordenes, "obtener órdenes pendientes")

        resultado = []
        tipos_orden = {2: "BUY LIMIT", 3: "SELL LIMIT", 4: "BUY STOP", 5: "SELL STOP"}
        for o in ordenes:
            t = getattr(o, "type", -1)
            resultado.append({
                "ticket": getattr(o, "ticket", None),
                "simbolo": getattr(o, "symbol", None),
                "tipo": tipos_orden.get(t, f"TIPO_{t}"),
                "lotes": _num(getattr(o, "volume_initial", None)),
                "precio_orden": _num(getattr(o, "price_open", None)),
                "sl": _nivel(getattr(o, "sl", None)),
                "tp": _nivel(getattr(o, "tp", None)),
            })

        return {
            "fuente": "MetaTrader 5",
            "total_ordenes": len(resultado),
            "ordenes": resultado,
            "consultado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }


def historial_operaciones(dias: int = 30, simbolo: str | None = None, ultimas: int = 15) -> dict[str, Any]:
    with _sesion() as mt5:
        hasta = datetime.now(timezone.utc)
        desde = hasta - timedelta(days=max(1, dias))
        sym_filter = _resolver(mt5, simbolo) if simbolo else None

        deals = mt5.history_deals_get(desde, hasta)
        deals = _como_tupla(mt5, deals, "obtener historial de operaciones")

        operaciones = []
        lucro_total = 0.0
        ganadoras = 0
        perdedoras = 0

        for d in deals:
            entry = getattr(d, "entry", None)
            deal_sym = getattr(d, "symbol", None)
            if entry in (1, 2):
                if sym_filter and deal_sym != sym_filter:
                    continue

                profit = _num(getattr(d, "profit", 0.0)) or 0.0
                lucro_total += profit

                if profit > 0:
                    ganadoras += 1
                elif profit < 0:
                    perdedoras += 1

                operaciones.append({
                    "ticket": getattr(d, "ticket", None),
                    "simbolo": deal_sym,
                    "tipo": "COMPRA" if getattr(d, "type", 0) == 0 else "VENTA",
                    "lotes": _num(getattr(d, "volume", None)),
                    "precio": _num(getattr(d, "price", None)),
                    "beneficio": profit,
                    "fecha_utc": _hora_utc(getattr(d, "time", 0), mt5),
                })

        total_ops = ganadoras + perdedoras
        win_rate = (ganadoras / total_ops * 100) if total_ops > 0 else 0.0

        return {
            "fuente": "MetaTrader 5",
            "dias_consultados": dias,
            "resumen": {
                "total_operaciones": total_ops,
                "ganadoras": ganadoras,
                "perdedoras": perdedoras,
                "tasa_acierto_pct": round(win_rate, 2),
                "beneficio_neto_total": round(lucro_total, 2),
            },
            "ultimas_operaciones": operaciones[-ultimas:] if ultimas > 0 else [],
            "consultado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }


def precio(simbolo: str) -> dict[str, Any]:
    with _sesion() as mt5:
        sym = _resolver(mt5, simbolo)
        with _simbolo_temporal(mt5, sym) as info:
            tick = mt5.symbol_info_tick(sym)
            if tick is None or info is None:
                raise ErrorMT5(f"No fue posible obtener el precio en tiempo real para '{sym}'.")

            bid = tick.bid
            ask = tick.ask
            spread = (ask - bid) if (ask and bid) else 0.0
            point = getattr(info, "point", 0.00001) or 0.00001
            spread_pips = round(spread / point, 1) if point > 0 else 0.0

            open_price = getattr(info, "session_open", 0.0) or bid
            var_pct = round(((bid - open_price) / open_price * 100), 2) if open_price else 0.0

            return {
                "fuente": "MetaTrader 5",
                "simbolo": sym,
                "bid": _num(bid),
                "ask": _num(ask),
                "spread_pips": spread_pips,
                "maximo_dia": _num(getattr(info, "high", None)),
                "minimo_dia": _num(getattr(info, "low", None)),
                "variacion_pct": var_pct,
                "fecha_utc": _hora_utc(tick.time, mt5),
            }


def velas(
    simbolo: str,
    timeframe: str = "H1",
    cantidad: int = 100,
    ultimas_velas: int = 20,
    desde: str | None = None,
    hasta: str | None = None,
) -> dict[str, Any]:
    if timeframe not in TIMEFRAMES:
        raise ErrorMT5(f"Timeframe inválido '{timeframe}'. Opciones: {list(TIMEFRAMES.keys())}")

    tf_val = TIMEFRAMES[timeframe]
    with _sesion() as mt5:
        sym = _resolver(mt5, simbolo)
        with _simbolo_temporal(mt5, sym):
            if desde:
                dt_desde = _fecha_utc(desde, "desde")
                dt_hasta = _fecha_utc(hasta, "hasta") if hasta else datetime.now(timezone.utc)
                rates = mt5.copy_rates_range(sym, tf_val, dt_desde, dt_hasta)
            else:
                rates = mt5.copy_rates_from_pos(sym, tf_val, 0, max(1, cantidad))

            rates = _como_tupla(mt5, rates, "obtener velas")
            if len(rates) == 0:
                raise ErrorMT5(f"No hay datos de velas para {sym}.")

            precios_cierre = [float(r[4]) for r in rates]
            maximos = [float(r[2]) for r in rates]
            minimos = [float(r[3]) for r in rates]

            primer_cierre = precios_cierre[0]
            ultimo_cierre = precios_cierre[-1]
            var_pct = ((ultimo_cierre - primer_cierre) / primer_cierre * 100) if primer_cierre else 0.0

            detalle = []
            if ultimas_velas > 0:
                for r in rates[-ultimas_velas:]:
                    detalle.append({
                        "fecha_utc": _hora_utc(r[0], mt5),
                        "open": _num(r[1]),
                        "high": _num(r[2]),
                        "low": _num(r[3]),
                        "close": _num(r[4]),
                        "volumen": int(r[5]),
                    })

            return {
                "fuente": "MetaTrader 5",
                "simbolo": sym,
                "timeframe": timeframe,
                "total_velas_evaluadas": len(rates),
                "resumen_rango": {
                    "precio_inicial": primer_cierre,
                    "precio_ultimo": ultimo_cierre,
                    "maximo_periodo": max(maximos),
                    "minimo_periodo": min(minimos),
                    "variacion_total_pct": round(var_pct, 2),
                },
                "ultimas_velas": detalle,
                "consultado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }


def buscar_simbolos(texto: str, max_resultados: int = 15) -> dict[str, Any]:
    with _sesion() as mt5:
        query = (texto or "").strip().upper()
        crudos = _como_tupla(mt5, mt5.symbols_get(), "listar los símbolos")

        coincidencias = []
        for s in crudos:
            sym = getattr(s, "name", "")
            desc = getattr(s, "description", "")
            if query in sym.upper() or query in desc.upper():
                coincidencias.append({
                    "simbolo": sym,
                    "descripcion": desc,
                    "categoria": getattr(s, "path", ""),
                })
                if len(coincidencias) >= max_resultados:
                    break

        return {
            "fuente": "MetaTrader 5",
            "busqueda": texto,
            "coincidencias_encontradas": len(coincidencias),
            "resultados": coincidencias,
        }