# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ----------------------------------- INICIO Piña y Jara ejecucion .PY ----------------------------------
# -------------------------------------------------------------------------------------------------------

"""Ejecución de la decisión (solo el motor ejecuta): valida, propone y confirma por nucleo_agente.ordenes."""
from __future__ import annotations

from typing import Any

from herramientas.tickets import ticket as _tk
from nucleo_agente import ordenes
from nucleo_agente.vigilancia.configuracion import MAX_ABIERTAS_POR_VIGILANCIA
from nucleo_agente.vigilancia.utilidades import _lado_texto, _notificar


# TITULO RESERVAR OPERACION

def _reservar_operacion(v: dict[str, Any]) -> bool:
    """Reserva, en UNA sola sentencia atómica, la siguiente operación de la vigilancia `v` si sigue ACTIVA, con la MISMA autorización (`autorizada`) con la que se pidió el análisis, sin vencer
    y sin haber agotado `max_operaciones`. False si el usuario la detuvo, la renovó o ya se usaron todas: entonces no se envía nada. También evita que dos chequeos simultáneos superen el máximo."""
    return ordenes._ejecutar(
        "UPDATE vigilancias SET operaciones = COALESCE(operaciones, 0) + 1 WHERE id = ? AND estado = 'ACTIVA' AND autorizada IS ? "
        "AND (vence IS NULL OR vence > ?) AND COALESCE(operaciones, 0) < max_operaciones",
        (v["id"], v.get("autorizada"), ordenes._ahora()),
    ) == 1


# TITULO LIBERAR OPERACION

def _liberar_operacion(v: dict[str, Any]) -> None:
    """Devuelve la operación reservada con `_reservar_operacion` cuando no llegó a abrirse."""
    ordenes._ejecutar("UPDATE vigilancias SET operaciones = MAX(COALESCE(operaciones, 0) - 1, 0) WHERE id = ?", (v["id"],))


# TITULO SIGUE AUTORIZADA

def _sigue_autorizada(v: dict[str, Any]) -> bool:
    """True si la vigilancia `v` sigue ACTIVA, con la misma autorización y sin vencer (se revalida justo antes de enviar un cierre)."""
    filas = ordenes._consultar(
        "SELECT 1 FROM vigilancias WHERE id = ? AND estado = 'ACTIVA' AND autorizada IS ? AND (vence IS NULL OR vence > ?)",
        (v["id"], v.get("autorizada"), ordenes._ahora()),
    )
    return bool(filas)


# TITULO APLICAR

def _aplicar(v: dict[str, Any], d: dict[str, Any], posiciones: list[Any]) -> str:
    """Valida y ejecuta la decisión del modelo; es el único punto donde la vigilancia opera.

    Recibe la vigilancia `v`, la decisión `d` (de parsear_decision) y las posiciones propias abiertas.
    Para abrir exige no superar la posición abierta ni el máximo de operaciones, y un lado y stop loss válidos;
    luego propone por ordenes.proponer_apertura (que aplica todos los límites de riesgo) y confirma de inmediato.
    Para cerrar exige el permiso de la vigilancia y que el ticket sea propio. Cada resultado notifica al usuario.
    Devuelve el resumen de una línea para el historial de la vigilancia."""
    # Símbolo de la vigilancia (el modelo no elige otro) y resumen de la decisión.
    simbolo, resumen = v["simbolo"], d.get("resumen") or ""
    if d["accion"] == "abrir":
        if len(posiciones) >= MAX_ABIERTAS_POR_VIGILANCIA:
            return f"Esperar: ya hay una posición abierta. {resumen}".strip()
        if (v.get("operaciones") or 0) >= v["max_operaciones"]:
            return "Esperar: se alcanzó el máximo de operaciones de esta vigilancia."
        if d["lado"] is None or d["stop_loss"] is None:
            return "No se abrió: la decisión no traía un lado y un stop loss válidos."
        # Alcance de la decisión: el modelo solo elige lado y niveles; el símbolo, el riesgo y el máximo de operaciones son los que el usuario autorizó (revalidados al reservar).
        if not _reservar_operacion(v):
            return "No se abrió: la autorización de la vigilancia ya no está vigente (detenida, renovada, vencida o sin operaciones disponibles)."
        # Se propone con el riesgo fijado en la vigilancia; los límites globales se aplican dentro.
        prop = ordenes.proponer_apertura(
            simbolo, d["lado"], d["stop_loss"], d["take_profit"], v["riesgo_pct"],
            resumen or "Operación automática de la vigilancia", origen="automatica", vigilancia_id=v["id"],
        )
        if prop.get("estado") != "PROPUESTA_PENDIENTE":
            _liberar_operacion(v)
            motivo = prop.get("motivo") or prop.get("mensaje") or "bloqueada por los límites de riesgo"
            _notificar(v, f"Operación bloqueada · {simbolo}", f"El agente quiso abrir {d['lado']} pero: {motivo}", tipo="error")
            return f"Bloqueada: {motivo}"
        # Como el usuario ya autorizó la vigilancia, el motor confirma la propuesta sin pasar por el panel.
        resultado = ordenes.confirmar_orden(prop["id"])
        if resultado.get("ok"):
            r = prop["resumen"]
            detalle = (f"{r['volumen']:g} lotes · SL {r['stop_loss']} · TP {r['take_profit'] or '—'} · "
                       f"riesgo {r['riesgo']}")
            _notificar(v, f"{_lado_texto(d['lado'])} automática · {simbolo}", f"{detalle}. {resultado.get('mensaje', '')}")
            return f"Abrió {d['lado']}: {resumen}".strip()
        _liberar_operacion(v)
        _notificar(v, f"No se pudo ejecutar · {simbolo}", resultado.get("mensaje", "Error al enviar la orden."), tipo="error")
        return f"No se ejecutó: {resultado.get('mensaje', '')}"
    if d["accion"] == "cerrar":
        if not v.get("permite_cerrar"):
            return "No se cerró: esta vigilancia no tiene permiso para cerrar."
        # Solo se puede cerrar una posición abierta por esta misma vigilancia; con una sola, el ticket es implícito.
        propias = {_tk(p.ticket): p for p in posiciones}
        ticket = d["ticket"] if d["ticket"] is not None else (next(iter(propias)) if len(propias) == 1 else None)
        if ticket not in propias:
            return "No se cerró: el ticket no corresponde a una posición abierta por esta vigilancia."
        resultado_actual = propias[ticket].profit
        if not _sigue_autorizada(v):
            return "No se cerró: la autorización de la vigilancia ya no está vigente."
        prop = ordenes.proponer_cierre(ticket, resumen or "Cierre automático de la vigilancia",
                                       origen="automatica", vigilancia_id=v["id"])
        if prop.get("estado") != "PROPUESTA_PENDIENTE":
            motivo = prop.get("motivo") or "no se pudo preparar el cierre"
            _notificar(v, f"No se pudo cerrar · {simbolo}", motivo, tipo="error")
            return f"No se cerró: {motivo}"
        resultado = ordenes.confirmar_orden(prop["id"])
        if resultado.get("ok"):
            _notificar(v, f"Posición cerrada · {simbolo}",
                       f"Resultado ≈ {resultado_actual:+.2f}. {resumen or resultado.get('mensaje', '')}".strip())
            return f"Cerró la posición #{ticket}: {resumen}".strip()
        _notificar(v, f"No se pudo cerrar · {simbolo}", resultado.get("mensaje", "Error al enviar la orden."), tipo="error")
        return f"No se cerró: {resultado.get('mensaje', '')}"
    # Cualquier otra acción equivale a esperar.
    return f"Esperar: {resumen}".strip()


# -------------------------------------------------------------------------------------------------------
# ------------------------------------ FIN Piña y Jara ejecucion .PY ------------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
