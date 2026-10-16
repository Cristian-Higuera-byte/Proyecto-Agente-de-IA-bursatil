"""Posiciones de una vigilancia (solo las que ella abrió, reconocidas por el comentario de la orden)."""
from __future__ import annotations

from typing import Any

from proveedores.selector_mt5 import mt5  # type: ignore[import-untyped]

from nucleo_agente import ordenes
from nucleo_agente.vigilancia.utilidades import _consultar


def _posiciones_de(v: dict[str, Any]) -> list[Any]:
    ids = {f["id"] for f in _consultar(
        "SELECT id FROM ordenes WHERE vigilancia_id = ? AND accion = 'abrir' AND estado = 'EJECUTADA'", (v["id"],))}
    if not ids:
        return []
    with ordenes.MT5_LOCK:
        abiertas = mt5.positions_get(symbol=v["simbolo"]) or []
    return [p for p in abiertas if (getattr(p, "comment", "") or "").rpartition(":")[2] in ids]
