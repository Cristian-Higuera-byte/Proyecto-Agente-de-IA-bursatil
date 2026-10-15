"""Ejecución de la decisión (solo el motor ejecuta): valida, propone y confirma por nucleo_agente.ordenes."""
from __future__ import annotations

from typing import Any

from nucleo_agente import ordenes
from nucleo_agente.vigilancia.configuracion import MAX_ABIERTAS_POR_VIGILANCIA
from nucleo_agente.vigilancia.utilidades import _lado_txt, _notificar


def _aplicar(v: dict[str, Any], d: dict[str, Any], posiciones: list[Any]) -> str:
    """Valida y ejecuta la decisión. Devuelve el resumen para el historial de la vigilancia."""
    sym, resumen = v["simbolo"], d.get("resumen") or ""
    if d["accion"] == "abrir":
        if len(posiciones) >= MAX_ABIERTAS_POR_VIGILANCIA:
            return f"Esperar: ya hay una posición abierta. {resumen}".strip()
        if (v.get("operaciones") or 0) >= v["max_operaciones"]:
            return "Esperar: se alcanzó el máximo de operaciones de esta vigilancia."
        if d["lado"] is None or d["stop_loss"] is None:
            return "No se abrió: la decisión no traía un lado y un stop loss válidos."
        prop = ordenes.proponer_apertura(
            sym, d["lado"], d["stop_loss"], d["take_profit"], v["riesgo_pct"],
            resumen or "Operación automática de la vigilancia", origen="automatica", vigilancia_id=v["id"],
        )
        if prop.get("estado") != "PROPUESTA_PENDIENTE":
            motivo = prop.get("motivo") or prop.get("mensaje") or "bloqueada por los límites de riesgo"
            _notificar(v, f"Operación bloqueada · {sym}", f"El agente quiso abrir {d['lado']} pero: {motivo}", tipo="error")
            return f"Bloqueada: {motivo}"
        res = ordenes.confirmar_orden(prop["id"])
        if res.get("ok"):
            ordenes._ejecutar("UPDATE vigilancias SET operaciones = operaciones + 1 WHERE id = ?", (v["id"],))
            r = prop["resumen"]
            detalle = (f"{r['volumen']:g} lotes · SL {r['stop_loss']} · TP {r['take_profit'] or '—'} · "
                       f"riesgo {r['riesgo']}")
            _notificar(v, f"{_lado_txt(d['lado'])} automática · {sym}", f"{detalle}. {res.get('mensaje', '')}")
            return f"Abrió {d['lado']}: {resumen}".strip()
        _notificar(v, f"No se pudo ejecutar · {sym}", res.get("mensaje", "Error al enviar la orden."), tipo="error")
        return f"No se ejecutó: {res.get('mensaje', '')}"
    if d["accion"] == "cerrar":
        if not v.get("permite_cerrar"):
            return "No se cerró: esta vigilancia no tiene permiso para cerrar."
        propias = {int(p.ticket): p for p in posiciones}
        ticket = d["ticket"] if d["ticket"] is not None else (next(iter(propias)) if len(propias) == 1 else None)
        if ticket not in propias:
            return "No se cerró: el ticket no corresponde a una posición abierta por esta vigilancia."
        resultado_actual = propias[ticket].profit
        prop = ordenes.proponer_cierre(ticket, resumen or "Cierre automático de la vigilancia",
                                       origen="automatica", vigilancia_id=v["id"])
        if prop.get("estado") != "PROPUESTA_PENDIENTE":
            motivo = prop.get("motivo") or "no se pudo preparar el cierre"
            _notificar(v, f"No se pudo cerrar · {sym}", motivo, tipo="error")
            return f"No se cerró: {motivo}"
        res = ordenes.confirmar_orden(prop["id"])
        if res.get("ok"):
            _notificar(v, f"Posición cerrada · {sym}",
                       f"Resultado ≈ {resultado_actual:+.2f}. {resumen or res.get('mensaje', '')}".strip())
            return f"Cerró la posición #{ticket}: {resumen}".strip()
        _notificar(v, f"No se pudo cerrar · {sym}", res.get("mensaje", "Error al enviar la orden."), tipo="error")
        return f"No se cerró: {res.get('mensaje', '')}"
    return f"Esperar: {resumen}".strip()
