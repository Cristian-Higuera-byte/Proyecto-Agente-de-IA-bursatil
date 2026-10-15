"""Validación de turnos: jamás se guarda ni se carga un turno por la mitad (un 'tool' sin su 'tool_calls' da 400)."""
from typing import Any


def _turno_valido(turno: list[dict[str, Any]]) -> bool:
    """Válido si cada 'tool' responde a un tool_call del asistente anterior
    y no queda ninguna llamada sin resultado."""
    pendientes: set[str] = set()
    for m in turno:
        rol = m.get("role")
        if rol == "tool":
            if m.get("tool_call_id") not in pendientes:
                return False
            pendientes.discard(m["tool_call_id"])
        else:
            if pendientes:
                return False
            if rol == "assistant":
                pendientes = {c["id"] for c in (m.get("tool_calls") or [])}
    return not pendientes


def _sanear(historial: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Conserva solo turnos completos y consistentes (cada turno empieza en un 'user')."""
    turnos: list[list[dict[str, Any]]] = []
    actual: list[dict[str, Any]] = []
    for msg in historial:
        if msg.get("role") == "user":
            if actual:
                turnos.append(actual)
            actual = [msg]
        elif actual:
            actual.append(msg)  # lo anterior al primer 'user' (turno cortado) se descarta
    if actual:
        turnos.append(actual)
    return [m for t in turnos if _turno_valido(t) for m in t]
