"""Órdenes del agente - FASE 1: el agente PROPONE, el usuario CONFIRMA.

NOMBRE DEL ARCHIVO: core/ordenes.py

Garantías de diseño:
  * El agente NO tiene ninguna herramienta que ejecute órdenes. Solo llama a
    proponer_apertura / proponer_cierre (ver herramientas/ordenes_tools.py), que
    validan contra LIMITES y guardan una propuesta PENDIENTE.
  * La única función que envía algo a MetaTrader 5 es confirmar_orden(), y solo la
    llama el botón "Confirmar" del dashboard (components/panel_ordenes.py).
  * Los límites de riesgo están en código (LIMITES), no en el prompt: el modelo no
    puede saltárselos ni cambiarlos.
  * Cada propuesta queda registrada en SQLite (data/ordenes.db) con su justificación:
    es el registro de auditoría de todo lo que el agente decidió.
  * Una propuesta solo se ejecuta una vez (se "reclama" de forma atómica), así que
    un doble clic o un reintento no duplica la orden.
"""

from __future__ import annotations

import functools
import math
import sqlite3
import threading
import time
import uuid
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5  # type: ignore[import-untyped]

from tools.mt5_bridge import MT5_LOCK, inicializar_mt5


# ══════════════════════════════════════════════════════════════
#  LÍMITES DE RIESGO  (edítalos aquí; el agente no puede cambiarlos)
# ══════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class LimitesRiesgo:
    solo_demo: bool = True                       # rechaza TODO si la cuenta conectada no es demo
    riesgo_max_por_operacion_pct: float = 1.0    # % del equity que se puede perder si salta el SL
    riesgo_max_total_pct: float = 3.0            # % del equity en riesgo sumando posiciones abiertas + propuestas pendientes + la nueva
    max_posiciones_abiertas: int = 3
    perdida_max_diaria_pct: float = 3.0          # % del balance; al alcanzarlo no se abren más
    volumen_max: float = 0.5                     # lotes máximos por orden
    vigencia_propuesta_min: int = 10             # minutos antes de que una propuesta venza
    desviacion_puntos: int = 20                  # deslizamiento máximo aceptado al ejecutar
    # Solo estos símbolos (ajusta los nombres a los de tu broker en MT5):
    simbolos_permitidos: tuple = ("EURUSD", "GBPUSD", "USDJPY", "USDCLP", "GOLD", "XAUUSD")


LIMITES = LimitesRiesgo()

MAGIC = 940731  # identifica en MT5 las órdenes enviadas desde este módulo
TOLERANCIA_RIESGO = 1.10  # al confirmar, el precio pudo moverse: se tolera hasta +10 % sobre el límite
TOLERANCIA_VS_PROPUESTA = 1.25  # al confirmar, el riesgo real no puede superar en más de 25 % lo que vio el usuario

DIR_DATOS = Path(__file__).resolve().parent.parent / "data"
DIR_DATOS.mkdir(exist_ok=True)
RUTA_DB = DIR_DATOS / "ordenes.db"


# ══════════════════════════════════════════════════════════════
#  Base de datos (SQLite): propuestas, auditoría e interruptor de emergencia
# ══════════════════════════════════════════════════════════════
_SQL_ORDENES = """
CREATE TABLE IF NOT EXISTS ordenes (
    id TEXT PRIMARY KEY,
    creada TEXT NOT NULL,
    expira TEXT NOT NULL,
    estado TEXT NOT NULL,        -- PENDIENTE | EJECUTANDO | EJECUTADA | RECHAZADA_USUARIO |
                                 -- RECHAZADA_RIESGO | EXPIRADA | ERROR
    accion TEXT NOT NULL,        -- abrir | cerrar
    simbolo TEXT,
    lado TEXT,                   -- compra | venta  (en 'cerrar': el lado de la posición)
    volumen REAL,
    precio_ref REAL,
    sl REAL,
    tp REAL,
    riesgo_dinero REAL,          -- en 'abrir': pérdida si salta el SL; en 'cerrar': P&L flotante
    riesgo_pct REAL,
    ticket_objetivo INTEGER,     -- en 'cerrar': ticket de la posición
    justificacion TEXT,
    detalle TEXT,                -- motivo del rechazo / resultado de la ejecución
    ticket_resultado INTEGER
)
"""


_DB_PREPARADA: Path | None = None   # ruta de la base ya inicializada en este proceso
_DB_LOCK = threading.Lock()


def _conectar() -> sqlite3.Connection:
    global _DB_PREPARADA
    con = sqlite3.connect(RUTA_DB, timeout=10)
    con.row_factory = sqlite3.Row
    if _DB_PREPARADA != RUTA_DB:  # las tablas se crean una sola vez, no en cada consulta
        with _DB_LOCK:
            try:
                con.execute("PRAGMA journal_mode=WAL")  # lecturas y escrituras no se bloquean entre sí
            except sqlite3.OperationalError:
                pass  # otra conexión la usa ahora mismo: se queda en el modo actual
            con.execute(_SQL_ORDENES)
            con.execute("CREATE TABLE IF NOT EXISTS estado (clave TEXT PRIMARY KEY, valor TEXT)")
            con.commit()
            _DB_PREPARADA = RUTA_DB
    return con


def _ejecutar(sql: str, params: tuple = ()) -> int:
    with closing(_conectar()) as con:
        with con:
            return con.execute(sql, params).rowcount


def _consultar(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    with closing(_conectar()) as con:
        return [dict(f) for f in con.execute(sql, params).fetchall()]


def _ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _insertar(**campos: Any) -> str:
    id_ = uuid.uuid4().hex[:8]
    ahora = datetime.now()
    base = {
        "id": id_,
        "creada": ahora.isoformat(timespec="seconds"),
        "expira": (ahora + timedelta(minutes=LIMITES.vigencia_propuesta_min)).isoformat(timespec="seconds"),
    }
    base.update(campos)
    columnas = ", ".join(base)
    marcas = ", ".join("?" for _ in base)
    _ejecutar(f"INSERT INTO ordenes ({columnas}) VALUES ({marcas})", tuple(base.values()))
    return id_


def kill_switch_activo() -> bool:
    filas = _consultar("SELECT valor FROM estado WHERE clave = 'kill_switch'")
    return bool(filas) and filas[0]["valor"] == "1"


def set_kill_switch(activo: bool) -> None:
    _ejecutar(
        "INSERT INTO estado (clave, valor) VALUES ('kill_switch', ?) "
        "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
        ("1" if activo else "0",),
    )


# ══════════════════════════════════════════════════════════════
#  Utilidades de MetaTrader 5
# ══════════════════════════════════════════════════════════════
def _normalizar(simbolo: str) -> str:
    return (simbolo or "").replace("...", "").replace("…", "").strip().upper()


def _con_lock(funcion):
    """Serializa el acceso a MT5 con el MISMO candado del resto de la app (MT5_LOCK).

    La API de MetaTrader 5 no es segura entre hilos y servidor_datos.py / los fragmentos en
    vivo leen MT5 en paralelo. Como es un RLock, anidar llamadas con este decorador es seguro.
    """
    @functools.wraps(funcion)
    def envuelta(*args: Any, **kwargs: Any) -> Any:
        with MT5_LOCK:
            return funcion(*args, **kwargs)
    return envuelta


def _preparar_mt5() -> str | None:
    """None si MT5 está listo; si no, el mensaje de error."""
    with MT5_LOCK:
        # inicializar_mt5 usa la ruta del terminal configurada (MT5_PATH) y no reintenta en bucle.
        if mt5.terminal_info() is None and not inicializar_mt5():
            return f"No se pudo conectar con MetaTrader 5: {mt5.last_error()}"
    return None


def _inicio_dia_servidor() -> int | None:
    """Epoch (en hora del SERVIDOR del broker) de las 00:00 de hoy, o None si no se puede saber.

    MT5 guarda las horas de las operaciones en hora del servidor, que no es la hora local: usar la
    medianoche local desfasa el "día" varias horas. Se toma la hora del último tick como reloj del
    servidor; si es viejo (fin de semana, mercado cerrado) no sirve y se usa el método local.
    """
    for simbolo in LIMITES.simbolos_permitidos:
        tick = mt5.symbol_info_tick(simbolo)
        if tick is not None and tick.time and abs(time.time() - tick.time) < 86400:
            return int(tick.time - tick.time % 86400)
    return None


def _perdida_del_dia(cuenta: Any) -> float:
    """Pérdida del día (número positivo): operaciones cerradas hoy + resultado flotante."""
    ahora = datetime.now()
    inicio_servidor = _inicio_dia_servidor()
    if inicio_servidor is None:
        desde = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        desde = ahora - timedelta(days=3)  # ventana amplia; luego se filtra por la hora del servidor
    deals = mt5.history_deals_get(desde, ahora + timedelta(days=1)) or []
    realizado = sum(
        d.profit + d.commission + d.swap
        for d in deals
        if d.type in (mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL)
        and (inicio_servidor is None or d.time >= inicio_servidor)
    )
    return max(0.0, -(realizado + cuenta.profit))


def _riesgo_expuesto(cuenta: Any, incluir_pendientes: bool) -> float:
    """Dinero que se perdería si saltaran TODOS los stop loss: posiciones abiertas (+ propuestas pendientes)."""
    total = 0.0
    for p in mt5.positions_get() or []:
        if p.sl:
            resultado = mt5.order_calc_profit(p.type, p.symbol, p.volume, p.price_open, p.sl)
            total += max(0.0, -resultado) if resultado is not None else 0.0
        else:  # sin stop loss el riesgo es desconocido: se asume el máximo por operación
            total += cuenta.equity * LIMITES.riesgo_max_por_operacion_pct / 100
    if incluir_pendientes:
        filas = _consultar(
            "SELECT COALESCE(SUM(riesgo_dinero), 0) AS total FROM ordenes "
            "WHERE estado = 'PENDIENTE' AND accion = 'abrir' AND expira > ?",
            (_ahora(),),
        )
        total += float(filas[0]["total"] or 0)
    return total


def _modo_llenado(info: Any) -> int:
    modo = info.filling_mode
    if modo & 2:
        return mt5.ORDER_FILLING_IOC
    if modo & 1:
        return mt5.ORDER_FILLING_FOK
    return mt5.ORDER_FILLING_RETURN


def _chequeos_globales(para_abrir: bool) -> tuple[Any, str | None]:
    """(cuenta, motivo_de_rechazo). Cerrar posiciones solo exige MT5 listo y cuenta demo."""
    error = _preparar_mt5()
    if error:
        return None, error
    cuenta = mt5.account_info()
    if cuenta is None:
        return None, "No se pudo leer la cuenta de MetaTrader 5."
    if LIMITES.solo_demo and cuenta.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
        return cuenta, "BLOQUEADO: la cuenta conectada NO es demo y la Fase 1 solo opera en cuenta demo."
    if para_abrir:
        if kill_switch_activo():
            return cuenta, "Las nuevas aperturas están bloqueadas (interruptor de emergencia activado por el usuario)."
        perdida = _perdida_del_dia(cuenta)
        tope = cuenta.balance * LIMITES.perdida_max_diaria_pct / 100
        if perdida >= tope:
            return cuenta, (
                f"Se alcanzó la pérdida máxima diaria ({perdida:.2f} de {tope:.2f} "
                f"{cuenta.currency}). No se abren más operaciones hoy."
            )
        abiertas = len(mt5.positions_get() or [])
        if abiertas >= LIMITES.max_posiciones_abiertas:
            return cuenta, f"Ya hay {abiertas} posiciones abiertas (máximo {LIMITES.max_posiciones_abiertas})."
    return cuenta, None


# ══════════════════════════════════════════════════════════════
#  Validación de una apertura (la usan la propuesta y, de nuevo, la confirmación)
# ══════════════════════════════════════════════════════════════
def _evaluar_apertura(
    cuenta: Any,
    simbolo: str,
    lado: str,
    stop_loss: Any,
    take_profit: Any,
    riesgo_pct: float | None,
    volumen_fijo: float | None = None,
    incluir_pendientes: bool = True,
) -> dict[str, Any]:
    def no(motivo: str) -> dict[str, Any]:
        return {"ok": False, "motivo": motivo}

    sym = _normalizar(simbolo)
    if sym not in {s.upper() for s in LIMITES.simbolos_permitidos}:
        return no(f"'{sym}' no está en la lista de símbolos permitidos: {', '.join(LIMITES.simbolos_permitidos)}.")

    lado = (lado or "").strip().lower()
    if lado not in ("compra", "venta"):
        return no("'lado' debe ser 'compra' o 'venta'.")
    es_compra = lado == "compra"

    try:
        sl = float(stop_loss)
    except (TypeError, ValueError):
        return no("El stop loss es obligatorio y debe ser un precio numérico.")
    tp: float | None = None
    if take_profit not in (None, "", 0):
        try:
            tp = float(take_profit)
        except (TypeError, ValueError):
            return no("El take profit debe ser un precio numérico.")

    mt5.symbol_select(sym, True)
    info = mt5.symbol_info(sym)
    if info is None:
        return no(f"El símbolo '{sym}' no existe en MetaTrader 5 (revisa el nombre exacto en tu broker).")
    if info.trade_mode != mt5.SYMBOL_TRADE_MODE_FULL:
        return no(f"'{sym}' no está disponible para operar en este momento (mercado cerrado o restringido).")

    tick = mt5.symbol_info_tick(sym)
    precio = (tick.ask if es_compra else tick.bid) if tick else 0.0
    if not precio:
        return no(f"No hay precio disponible para '{sym}' ahora mismo.")

    # Dirección de SL / TP respecto al precio
    if es_compra and not sl < precio:
        return no(f"En una compra el stop loss debe estar por DEBAJO del precio ({precio}).")
    if not es_compra and not sl > precio:
        return no(f"En una venta el stop loss debe estar por ENCIMA del precio ({precio}).")
    if tp is not None:
        if es_compra and not tp > precio:
            return no(f"En una compra el take profit debe estar por ENCIMA del precio ({precio}).")
        if not es_compra and not tp < precio:
            return no(f"En una venta el take profit debe estar por DEBAJO del precio ({precio}).")

    # Distancia mínima que exige el broker
    dist_min = info.trade_stops_level * info.point
    if abs(precio - sl) < dist_min or (tp is not None and abs(tp - precio) < dist_min):
        return no(f"SL/TP demasiado cerca del precio: el broker exige al menos {dist_min:.{info.digits}f} de distancia.")

    tipo = mt5.ORDER_TYPE_BUY if es_compra else mt5.ORDER_TYPE_SELL
    perdida_1_lote = mt5.order_calc_profit(tipo, sym, 1.0, precio, sl)
    if not perdida_1_lote:
        return no("No se pudo calcular el riesgo de la operación en MetaTrader 5.")
    perdida_1_lote = abs(perdida_1_lote)

    if volumen_fijo is None:
        if riesgo_pct is None or riesgo_pct <= 0:
            return no("'riesgo_pct' debe ser mayor que 0.")
        if riesgo_pct > LIMITES.riesgo_max_por_operacion_pct:
            return no(
                f"El riesgo pedido ({riesgo_pct}%) supera el máximo permitido por operación "
                f"({LIMITES.riesgo_max_por_operacion_pct}%)."
            )
        paso = info.volume_step or 0.01
        decimales = max(0, int(round(-math.log10(paso))))
        volumen = (cuenta.equity * riesgo_pct / 100) / perdida_1_lote
        volumen = math.floor(volumen / paso + 1e-9) * paso
        volumen = round(min(volumen, info.volume_max, LIMITES.volumen_max), decimales)
        if volumen < info.volume_min:
            return no(
                f"Con {riesgo_pct}% de riesgo y ese stop loss no alcanza ni el lote mínimo "
                f"({info.volume_min}). Acerca el stop loss o sube el riesgo (máx. "
                f"{LIMITES.riesgo_max_por_operacion_pct}%)."
            )
    else:
        volumen = float(volumen_fijo)

    riesgo_dinero = volumen * perdida_1_lote
    riesgo_pct_real = riesgo_dinero / cuenta.equity * 100
    if riesgo_pct_real > LIMITES.riesgo_max_por_operacion_pct * TOLERANCIA_RIESGO:
        return no(
            f"Con el precio actual el riesgo sería {riesgo_pct_real:.2f}%, sobre el máximo permitido "
            f"({LIMITES.riesgo_max_por_operacion_pct}%)."
        )

    expuesto = _riesgo_expuesto(cuenta, incluir_pendientes)
    total_pct = (expuesto + riesgo_dinero) / cuenta.equity * 100
    if total_pct > LIMITES.riesgo_max_total_pct * TOLERANCIA_RIESGO:
        return no(
            f"Riesgo total demasiado alto: con esta operación quedaría {total_pct:.2f}% del equity en riesgo "
            f"(posiciones abiertas y propuestas pendientes incluidas; máximo {LIMITES.riesgo_max_total_pct}%). "
            "Cierra posiciones, rechaza propuestas pendientes o reduce el riesgo."
        )

    margen = mt5.order_calc_margin(tipo, sym, volumen, precio)
    if margen is not None and margen > cuenta.margin_free:
        return no(f"Margen libre insuficiente (se necesitan {margen:.2f}, hay {cuenta.margin_free:.2f}).")

    return {
        "ok": True,
        "datos": {
            "simbolo": sym, "lado": lado, "tipo": tipo, "volumen": volumen, "precio": precio,
            "sl": sl, "tp": tp, "riesgo_dinero": riesgo_dinero, "riesgo_pct": riesgo_pct_real,
            "moneda": cuenta.currency,
        },
    }


def _propuesta_pendiente(accion: str, **filtros: Any) -> str | None:
    """id de una propuesta PENDIENTE (no vencida) con esa acción y esos campos, o None."""
    condiciones = "".join(f" AND {campo} = ?" for campo in filtros)  # los nombres de campo son fijos, no vienen del agente
    filas = _consultar(
        f"SELECT id FROM ordenes WHERE estado = 'PENDIENTE' AND accion = ? AND expira > ?{condiciones} "
        "ORDER BY creada LIMIT 1",
        (accion, _ahora(), *filtros.values()),
    )
    return filas[0]["id"] if filas else None


def _respuesta_duplicada(id_: str) -> dict[str, Any]:
    return {
        "estado": "PROPUESTA_DUPLICADA",
        "id": id_,
        "mensaje": (
            "Ya existe una propuesta pendiente igual (no se creó otra). No vuelvas a proponerla: dile al "
            "usuario que la confirme o la rechace en el panel de órdenes propuestas."
        ),
    }


# ══════════════════════════════════════════════════════════════
#  API para el AGENTE (solo proponer / consultar; NADA se ejecuta aquí)
# ══════════════════════════════════════════════════════════════
@_con_lock
def proponer_apertura(
    simbolo: str, lado: str, stop_loss: Any, take_profit: Any, riesgo_pct: float, justificacion: str,
) -> dict[str, Any]:
    cuenta, motivo = _chequeos_globales(para_abrir=True)
    if not motivo:
        previa = _propuesta_pendiente("abrir", simbolo=_normalizar(simbolo), lado=str(lado).strip().lower())
        if previa:
            return _respuesta_duplicada(previa)
    ev: dict[str, Any] | None = None
    if not motivo:
        ev = _evaluar_apertura(cuenta, simbolo, lado, stop_loss, take_profit, riesgo_pct)
        if ev is not None and not ev["ok"]:
            motivo = ev["motivo"]

    if motivo:
        _insertar(
            estado="RECHAZADA_RIESGO", accion="abrir", simbolo=_normalizar(simbolo), lado=str(lado).lower(),
            justificacion=justificacion, detalle=motivo,
        )
        return {"estado": "RECHAZADA", "motivo": motivo}

    assert ev is not None and ev["ok"]
    d = ev["datos"]
    id_ = _insertar(
        estado="PENDIENTE", accion="abrir", simbolo=d["simbolo"], lado=d["lado"], volumen=d["volumen"],
        precio_ref=d["precio"], sl=d["sl"], tp=d["tp"], riesgo_dinero=d["riesgo_dinero"],
        riesgo_pct=d["riesgo_pct"], justificacion=justificacion,
    )
    return {
        "estado": "PROPUESTA_PENDIENTE",
        "id": id_,
        "resumen": {
            "simbolo": d["simbolo"], "lado": d["lado"], "volumen": d["volumen"],
            "precio_referencia": d["precio"], "stop_loss": d["sl"], "take_profit": d["tp"],
            "riesgo": f"{d['riesgo_dinero']:.2f} {d['moneda']} ({d['riesgo_pct']:.2f}% del equity)",
            "vigencia_minutos": LIMITES.vigencia_propuesta_min,
        },
        "mensaje": (
            "Propuesta registrada, pero NO está ejecutada: el usuario debe confirmarla con el botón del "
            "dashboard. No afirmes que la orden fue enviada o ejecutada; di que queda pendiente de su confirmación."
        ),
    }


@_con_lock
def proponer_cierre(ticket: Any, justificacion: str) -> dict[str, Any]:
    cuenta, motivo = _chequeos_globales(para_abrir=False)

    def rechazo(txt: str) -> dict[str, Any]:
        _insertar(estado="RECHAZADA_RIESGO", accion="cerrar", justificacion=justificacion, detalle=txt)
        return {"estado": "RECHAZADA", "motivo": txt}

    if motivo:
        return rechazo(motivo)
    try:
        ticket = int(ticket)
    except (TypeError, ValueError):
        return rechazo("El ticket debe ser un número entero (usa ver_posiciones para consultarlo).")
    previa = _propuesta_pendiente("cerrar", ticket_objetivo=ticket)
    if previa:
        return _respuesta_duplicada(previa)
    posiciones = mt5.positions_get(ticket=ticket)
    if not posiciones:
        return rechazo(f"No existe una posición abierta con ticket {ticket}.")

    p = posiciones[0]
    es_compra = p.type == mt5.POSITION_TYPE_BUY
    tick = mt5.symbol_info_tick(p.symbol)
    precio = (tick.bid if es_compra else tick.ask) if tick else p.price_current
    id_ = _insertar(
        estado="PENDIENTE", accion="cerrar", simbolo=p.symbol, lado="compra" if es_compra else "venta",
        volumen=p.volume, precio_ref=precio, sl=p.sl or None, tp=p.tp or None,
        riesgo_dinero=p.profit, ticket_objetivo=ticket, justificacion=justificacion,
    )
    return {
        "estado": "PROPUESTA_PENDIENTE",
        "id": id_,
        "resumen": {
            "accion": "cerrar posición", "ticket": ticket, "simbolo": p.symbol, "volumen": p.volume,
            "resultado_actual": f"{p.profit:.2f} {cuenta.currency}",
        },
        "mensaje": (
            "Propuesta de cierre registrada, pero NO está ejecutada: el usuario debe confirmarla con el botón "
            "del dashboard. No afirmes que la posición fue cerrada."
        ),
    }


@_con_lock
def resumen_posiciones() -> dict[str, Any]:
    error = _preparar_mt5()
    if error:
        return {"error": error}
    cuenta = mt5.account_info()
    if cuenta is None:
        return {"error": "No se pudo leer la cuenta de MetaTrader 5."}
    posiciones = [
        {
            "ticket": p.ticket, "simbolo": p.symbol,
            "tipo": "compra" if p.type == mt5.POSITION_TYPE_BUY else "venta",
            "volumen": p.volume, "precio_apertura": p.price_open, "precio_actual": p.price_current,
            "stop_loss": p.sl or None, "take_profit": p.tp or None, "resultado": round(p.profit, 2),
        }
        for p in (mt5.positions_get() or [])
    ]
    return {
        "cuenta": {
            "tipo": "demo" if cuenta.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO else "REAL",
            "moneda": cuenta.currency, "balance": cuenta.balance, "equity": cuenta.equity,
            "margen_libre": cuenta.margin_free, "resultado_flotante": cuenta.profit,
        },
        "posiciones_abiertas": posiciones,
    }


@_con_lock
def estado_riesgo() -> dict[str, Any]:
    out: dict[str, Any] = {"limites": asdict(LIMITES), "interruptor_emergencia": kill_switch_activo()}
    error = _preparar_mt5()
    cuenta = None if error else mt5.account_info()
    if cuenta is not None:
        out["perdida_del_dia"] = round(_perdida_del_dia(cuenta), 2)
        out["posiciones_abiertas"] = len(mt5.positions_get() or [])
        out["riesgo_en_juego"] = round(_riesgo_expuesto(cuenta, incluir_pendientes=True), 2)  # abiertas + pendientes
        out["moneda"] = cuenta.currency
    return out


# ══════════════════════════════════════════════════════════════
#  API para el DASHBOARD (confirmar / rechazar / listar)
# ══════════════════════════════════════════════════════════════
def expirar_vencidas() -> None:
    """Marca como vencidas las propuestas pendientes que ya pasaron su hora y recupera las atascadas."""
    # Una orden "EJECUTANDO" mucho después de su vencimiento quedó a medias (se cayó la app al enviarla).
    # No se asume que falló: se avisa para que el usuario lo compruebe en MT5.
    limite = (datetime.now() - timedelta(seconds=60)).isoformat(timespec="seconds")
    _ejecutar(
        "UPDATE ordenes SET estado = 'ERROR', detalle = ? WHERE estado = 'EJECUTANDO' AND expira <= ?",
        ("Envío interrumpido: revisa en MetaTrader 5 si la orden llegó a abrirse o cerrarse.", limite),
    )
    _ejecutar("UPDATE ordenes SET estado = 'EXPIRADA' WHERE estado = 'PENDIENTE' AND expira <= ?", (_ahora(),))


def listar_pendientes() -> list[dict[str, Any]]:
    expirar_vencidas()
    return _consultar("SELECT * FROM ordenes WHERE estado = 'PENDIENTE' ORDER BY creada, rowid")


def listar_historial(limite: int = 15) -> list[dict[str, Any]]:
    return _consultar("SELECT * FROM ordenes ORDER BY creada DESC, rowid DESC LIMIT ?", (int(limite),))


def rechazar_orden(id_orden: str) -> bool:
    return _ejecutar(
        "UPDATE ordenes SET estado = 'RECHAZADA_USUARIO' WHERE id = ? AND estado = 'PENDIENTE'", (id_orden,)
    ) == 1


def confirmar_orden(id_orden: str) -> dict[str, Any]:
    """ÚNICO punto que envía órdenes a MT5. Solo lo llama el botón Confirmar del dashboard."""
    # Se "reclama" la propuesta de forma atómica: si ya se ejecutó, venció o fue rechazada, no se repite.
    reclamada = _ejecutar(
        "UPDATE ordenes SET estado = 'EJECUTANDO' WHERE id = ? AND estado = 'PENDIENTE' AND expira > ?",
        (id_orden, _ahora()),
    )
    if reclamada == 0:
        filas = _consultar("SELECT estado FROM ordenes WHERE id = ?", (id_orden,))
        if not filas:
            return {"ok": False, "mensaje": "La orden no existe."}
        if filas[0]["estado"] == "PENDIENTE":
            _ejecutar("UPDATE ordenes SET estado = 'EXPIRADA' WHERE id = ? AND estado = 'PENDIENTE'", (id_orden,))
            return {"ok": False, "mensaje": "La propuesta venció. Pídele al agente que la genere de nuevo."}
        return {"ok": False, "mensaje": f"La orden ya está en estado {filas[0]['estado']}; no se vuelve a ejecutar."}

    o = _consultar("SELECT * FROM ordenes WHERE id = ?", (id_orden,))[0]
    try:
        res = _enviar_apertura(o) if o["accion"] == "abrir" else _enviar_cierre(o)
    except Exception as e:  # noqa: BLE001
        res = {"ok": False, "estado": "ERROR", "mensaje": f"Error inesperado (revisa MT5 por si la orden se envió): {e}"}

    _ejecutar(
        "UPDATE ordenes SET estado = ?, detalle = ?, ticket_resultado = ? WHERE id = ?",
        ("EJECUTADA" if res["ok"] else res.get("estado", "ERROR"), res["mensaje"], res.get("ticket"), id_orden),
    )
    return res


@_con_lock
def _enviar_apertura(o: dict[str, Any]) -> dict[str, Any]:
    cuenta, motivo = _chequeos_globales(para_abrir=True)
    if motivo:
        return {"ok": False, "estado": "RECHAZADA_RIESGO", "mensaje": motivo}
    # Se revalida con el precio actual y el MISMO volumen propuesto.
    ev = _evaluar_apertura(cuenta, o["simbolo"], o["lado"], o["sl"], o["tp"], None, volumen_fijo=o["volumen"],
                           incluir_pendientes=False)
    if not ev["ok"]:
        return {"ok": False, "estado": "RECHAZADA_RIESGO", "mensaje": ev["motivo"]}

    d = ev["datos"]
    aprobado = o["riesgo_dinero"] or 0
    if aprobado and d["riesgo_dinero"] > aprobado * TOLERANCIA_VS_PROPUESTA:
        return {
            "ok": False, "estado": "RECHAZADA_RIESGO",
            "mensaje": (
                f"El precio se movió: el riesgo pasó de {aprobado:.2f} a {d['riesgo_dinero']:.2f} {d['moneda']}, "
                "más de lo que aprobaste. Pídele al agente una propuesta nueva."
            ),
        }
    info = mt5.symbol_info(d["simbolo"])
    solicitud = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": d["simbolo"], "volume": d["volumen"], "type": d["tipo"],
        "price": d["precio"], "sl": d["sl"], "deviation": LIMITES.desviacion_puntos, "magic": MAGIC,
        "comment": f"agente-ia:{o['id']}", "type_time": mt5.ORDER_TIME_GTC, "type_filling": _modo_llenado(info),
    }
    if d["tp"] is not None:
        solicitud["tp"] = d["tp"]
    return _interpretar(mt5.order_send(solicitud), f"{d['lado']} {d['volumen']} {d['simbolo']}")


@_con_lock
def _enviar_cierre(o: dict[str, Any]) -> dict[str, Any]:
    _, motivo = _chequeos_globales(para_abrir=False)
    if motivo:
        return {"ok": False, "estado": "RECHAZADA_RIESGO", "mensaje": motivo}
    posiciones = mt5.positions_get(ticket=int(o["ticket_objetivo"]))
    if not posiciones:
        return {"ok": False, "estado": "ERROR", "mensaje": "La posición ya no existe (¿se cerró antes?)."}
    p = posiciones[0]
    es_compra = p.type == mt5.POSITION_TYPE_BUY
    tick = mt5.symbol_info_tick(p.symbol)
    if tick is None:
        return {"ok": False, "estado": "ERROR", "mensaje": f"Sin precio disponible para {p.symbol}."}
    solicitud = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": p.symbol, "volume": p.volume,
        "type": mt5.ORDER_TYPE_SELL if es_compra else mt5.ORDER_TYPE_BUY, "position": p.ticket,
        "price": tick.bid if es_compra else tick.ask, "deviation": LIMITES.desviacion_puntos, "magic": MAGIC,
        "comment": f"agente-ia:{o['id']}", "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": _modo_llenado(mt5.symbol_info(p.symbol)),
    }
    return _interpretar(mt5.order_send(solicitud), f"cierre de la posición #{p.ticket} ({p.symbol})")


def _interpretar(resultado: Any, descripcion: str) -> dict[str, Any]:
    if resultado is None:
        return {"ok": False, "estado": "ERROR", "mensaje": f"MT5 no respondió: {mt5.last_error()}"}
    if resultado.retcode not in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_DONE_PARTIAL):
        return {
            "ok": False, "estado": "ERROR",
            "mensaje": f"MT5 rechazó la orden (código {resultado.retcode}): {resultado.comment}",
        }
    parcial = " (ejecución parcial)" if resultado.retcode == mt5.TRADE_RETCODE_DONE_PARTIAL else ""
    return {
        "ok": True, "ticket": resultado.order,
        "mensaje": f"Ejecutado{parcial}: {descripcion} a {resultado.price} (ticket #{resultado.order}).",
    }