"""API para el AGENTE: solo proponer / consultar. NADA se ejecuta aquí."""
from dataclasses import asdict
from typing import Any

from proveedores.selector_mt5 import mt5  # type: ignore[import-untyped]

from nucleo_agente.ordenes.base_datos import _ahora, _consultar, _insertar, kill_switch_activo
from nucleo_agente.ordenes.limites import LIMITES
from nucleo_agente.ordenes.mt5_utiles import (_chequeos_globales, _con_lock, _perdida_del_dia, _preparar_mt5,
                                     _resolver_simbolo, _riesgo_expuesto)
from nucleo_agente.ordenes.validacion import _evaluar_apertura


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


@_con_lock
def proponer_apertura(
    simbolo: str, lado: str, stop_loss: Any, take_profit: Any, riesgo_pct: float, justificacion: str,
    origen: str = "agente", vigilancia_id: str | None = None,
) -> dict[str, Any]:
    cuenta, motivo = _chequeos_globales(para_abrir=True)
    if not motivo:
        previa = _propuesta_pendiente("abrir", simbolo=_resolver_simbolo(simbolo), lado=str(lado).strip().lower())
        if previa:
            return _respuesta_duplicada(previa)
    ev: dict[str, Any] | None = None
    if not motivo:
        ev = _evaluar_apertura(cuenta, simbolo, lado, stop_loss, take_profit, riesgo_pct)
        if ev is not None and not ev["ok"]:
            motivo = ev["motivo"]

    if motivo:
        _insertar(
            estado="RECHAZADA_RIESGO", accion="abrir", simbolo=_resolver_simbolo(simbolo), lado=str(lado).lower(),
            justificacion=justificacion, detalle=motivo, origen=origen, vigilancia_id=vigilancia_id,
        )
        return {"estado": "RECHAZADA", "motivo": motivo}

    assert ev is not None and ev["ok"]
    d = ev["datos"]
    id_ = _insertar(
        estado="PENDIENTE", accion="abrir", simbolo=d["simbolo"], lado=d["lado"], volumen=d["volumen"],
        precio_ref=d["precio"], sl=d["sl"], tp=d["tp"], riesgo_dinero=d["riesgo_dinero"],
        riesgo_pct=d["riesgo_pct"], justificacion=justificacion, origen=origen, vigilancia_id=vigilancia_id,
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
def proponer_cierre(
    ticket: Any, justificacion: str, origen: str = "agente", vigilancia_id: str | None = None,
) -> dict[str, Any]:
    cuenta, motivo = _chequeos_globales(para_abrir=False)

    def rechazo(txt: str) -> dict[str, Any]:
        _insertar(estado="RECHAZADA_RIESGO", accion="cerrar", justificacion=justificacion, detalle=txt,
                  origen=origen, vigilancia_id=vigilancia_id)
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
        origen=origen, vigilancia_id=vigilancia_id,
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
