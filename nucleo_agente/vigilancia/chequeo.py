"""Chequeo de una vigilancia: analiza el activo y, si el modelo lo decide, ejecuta. Lo lanza el motor."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import MetaTrader5 as mt5  # type: ignore[import-untyped]

from nucleo_agente import ordenes
from nucleo_agente.vigilancia import analisis
from nucleo_agente.vigilancia.analisis import _mensaje_analisis
from nucleo_agente.vigilancia.configuracion import ACTIVA, ERROR, ERRORES_SEGUIDOS_MAX, FINALIZADA
from nucleo_agente.vigilancia.decision import parsear_decision
from nucleo_agente.vigilancia.ejecucion import _aplicar
from nucleo_agente.vigilancia.posiciones import _posiciones_de
from nucleo_agente.vigilancia.utilidades import _actualizar, _finalizar, _iso, obtener


def chequear(vid: str) -> dict[str, Any]:
    """Un chequeo: analiza el activo y, si el modelo lo decide, ejecuta. Lo lanza el motor."""
    v = obtener(vid)
    if not v or v["estado"] != ACTIVA:
        return {"ok": False, "motivo": "La vigilancia no está activa."}
    ahora = datetime.now()
    _actualizar(vid, ultimo_chequeo=_iso(ahora), chequeos=(v.get("chequeos") or 0) + 1,
                proximo_chequeo=_iso(ahora + timedelta(minutes=int(v["intervalo_min"]))))
    v = obtener(vid) or v

    cuenta, motivo = ordenes.cuenta_demo()
    if motivo and cuenta is not None:      # MT5 responde pero la cuenta NO es demo: se detiene todo
        _finalizar(v, ERROR, f"Vigilancia detenida · {v['simbolo']}", motivo, tipo="error")
        return {"ok": False, "motivo": motivo}
    if motivo:                              # MT5 sin conexión: se reintenta en el próximo chequeo
        _actualizar(vid, ultimo_resumen=f"Sin conexión con MetaTrader 5; se reintenta. ({motivo})"[:300])
        return {"ok": False, "motivo": motivo}

    posiciones = _posiciones_de(v)
    if (v.get("operaciones") or 0) >= v["max_operaciones"] and not posiciones:
        _finalizar(v, FINALIZADA, f"Vigilancia finalizada · {v['simbolo']}",
                   f"Se realizaron las {v['max_operaciones']} operaciones previstas y no queda ninguna posición abierta.")
        return {"ok": True, "estado": FINALIZADA}
    if ordenes.kill_switch_activo() and not posiciones:
        _actualizar(vid, ultimo_resumen="En pausa: el interruptor de emergencia bloquea las aperturas.")
        return {"ok": True, "estado": "EN_PAUSA"}

    with ordenes.MT5_LOCK:
        tick = mt5.symbol_info_tick(v["simbolo"])
    hora_tick = int(tick.time) if tick is not None and getattr(tick, "time", 0) else None
    if hora_tick is not None and v.get("ultimo_tick") == hora_tick:   # nada se movió: no se gastan tokens
        _actualizar(vid, ultimo_resumen="Mercado sin movimiento desde el último chequeo: no se analizó.")
        return {"ok": True, "estado": "SIN_MOVIMIENTO"}

    try:
        texto = analisis.fabrica_agente().responder(_mensaje_analisis(v, posiciones))
    except Exception as e:  # noqa: BLE001 - el fallo del modelo no debe tumbar el motor
        errores = (v.get("errores") or 0) + 1
        _actualizar(vid, errores=errores, ultimo_resumen=f"Falló el análisis: {e}"[:300])
        if errores >= ERRORES_SEGUIDOS_MAX:
            _finalizar(v, ERROR, f"Vigilancia detenida · {v['simbolo']}",
                       f"El análisis falló {errores} veces seguidas: {e}", tipo="error")
        return {"ok": False, "motivo": str(e)}

    actual = obtener(vid)
    if not actual or actual["estado"] != ACTIVA:   # el usuario la detuvo mientras el modelo pensaba
        return {"ok": False, "motivo": "La vigilancia fue detenida durante el análisis; se descartó la decisión."}
    decision = parsear_decision(texto)
    resumen = _aplicar(actual, decision, _posiciones_de(actual))
    _actualizar(vid, errores=0, ultimo_tick=hora_tick, ultimo_resumen=f"{ahora:%H:%M} · {resumen}"[:300])
    return {"ok": True, "decision": decision, "resumen": resumen}
