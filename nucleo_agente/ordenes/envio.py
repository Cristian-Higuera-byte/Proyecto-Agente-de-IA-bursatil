"""Envío de órdenes a MetaTrader 5 (apertura y cierre) e interpretación del resultado. Solo lo llama confirmar_orden()."""
from typing import Any

from proveedores.selector_mt5 import mt5  # type: ignore[import-untyped]

from nucleo_agente.ordenes.limites import MAGIC, TOLERANCIA_VS_PROPUESTA
from nucleo_agente.ordenes.mt5_utiles import _chequeos_globales, _con_lock, _desviacion, _modo_llenado
from nucleo_agente.ordenes.validacion import _evaluar_apertura


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
        "price": d["precio"], "sl": d["sl"], "deviation": _desviacion(info), "magic": MAGIC,
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
    info_cierre = mt5.symbol_info(p.symbol)
    solicitud = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": p.symbol, "volume": p.volume,
        "type": mt5.ORDER_TYPE_SELL if es_compra else mt5.ORDER_TYPE_BUY, "position": p.ticket,
        "price": tick.bid if es_compra else tick.ask, "deviation": _desviacion(info_cierre), "magic": MAGIC,
        "comment": f"agente-ia:{o['id']}", "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": _modo_llenado(info_cierre),
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
