"""Validación de una apertura (la usan la propuesta y, de nuevo, la confirmación) y utilidades de la vigilancia."""
import math
from typing import Any

import MetaTrader5 as mt5  # type: ignore[import-untyped]

from nucleo_agente.ordenes.limites import LIMITES, TOLERANCIA_RIESGO
from nucleo_agente.ordenes.mt5_utiles import (_con_lock, _normalizar, _preparar_mt5, _resolver_simbolo, _riesgo_expuesto)


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

    sym = _resolver_simbolo(simbolo)
    pedido = {sym.upper(), _normalizar(simbolo)}
    if LIMITES.simbolos_permitidos is not None and not (pedido & {s.upper() for s in LIMITES.simbolos_permitidos}):
        return no(f"'{sym}' no está entre los símbolos permitidos: {', '.join(LIMITES.simbolos_permitidos)}.")
    if pedido & {s.upper() for s in LIMITES.simbolos_bloqueados}:
        return no(f"'{sym}' está bloqueado para operar con el agente.")

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
        return no(f"El símbolo '{sym}' no existe en MetaTrader 5. Busca el nombre exacto con la búsqueda de "
                  "símbolos (mt5_buscar_simbolos) antes de volver a proponer.")
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


@_con_lock
def validar_simbolo(simbolo: str) -> dict[str, Any]:
    """Comprueba que un símbolo se puede operar: existe en MT5, está permitido (si hay lista) y no está
    bloqueado. Devuelve {"ok": True, "simbolo": nombre_real} o {"ok": False, "motivo": ...}.
    Mismas reglas que _evaluar_apertura; se usa para rechazar una vigilancia antes de crearla."""
    sym = _resolver_simbolo(simbolo)
    pedido = {sym.upper(), _normalizar(simbolo)}
    if not sym:
        return {"ok": False, "motivo": "Indica el símbolo del activo."}
    if LIMITES.simbolos_permitidos is not None and not (pedido & {s.upper() for s in LIMITES.simbolos_permitidos}):
        return {"ok": False, "motivo": f"'{sym}' no está entre los símbolos permitidos: {', '.join(LIMITES.simbolos_permitidos)}."}
    if pedido & {s.upper() for s in LIMITES.simbolos_bloqueados}:
        return {"ok": False, "motivo": f"'{sym}' está bloqueado para operar con el agente."}
    mt5.symbol_select(sym, True)
    info = mt5.symbol_info(sym)
    if info is None:
        return {"ok": False, "motivo": f"El símbolo '{sym}' no existe en MetaTrader 5. Busca el nombre exacto "
                                       "con la búsqueda de símbolos (mt5_buscar_simbolos)."}
    if info.trade_mode != mt5.SYMBOL_TRADE_MODE_FULL:
        return {"ok": False, "motivo": f"'{sym}' no está disponible para operar en este momento (mercado cerrado o restringido)."}
    return {"ok": True, "simbolo": sym}


@_con_lock
def cuenta_demo() -> tuple[Any, str | None]:
    """(cuenta, motivo). motivo es None solo si MT5 responde Y la cuenta es DEMO. La operación automática
    exige demo SIEMPRE, aunque LIMITES.solo_demo se relaje para las propuestas manuales."""
    error = _preparar_mt5()
    if error:
        return None, error
    cuenta = mt5.account_info()
    if cuenta is None:
        return None, "No se pudo leer la cuenta de MetaTrader 5."
    if cuenta.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
        return cuenta, "La operación automática solo está permitida en cuenta DEMO y la cuenta conectada no lo es."
    return cuenta, None
