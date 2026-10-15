"""Decisión del modelo: lee el bloque ```decision {...}``` del final de la respuesta."""
from __future__ import annotations

import json
import re
from typing import Any

from nucleo_agente.vigilancia.utilidades import _a_numero


_RE_OBJETO = re.compile(r"\{[^{}]*\}", re.S)
_SINONIMOS = {
    "espera": "esperar", "esperar": "esperar", "wait": "esperar", "hold": "esperar", "mantener": "esperar",
    "abrir": "abrir", "open": "abrir", "comprar": "abrir", "vender": "abrir",
    "cerrar": "cerrar", "close": "cerrar",
}


def parsear_decision(texto: str) -> dict[str, Any]:
    """Lee el bloque ```decision {...}``` del final de la respuesta. Si no hay uno válido, la decisión es
    ESPERAR (nunca se opera por una respuesta que no se entiende)."""
    candidatos = []
    for m in _RE_OBJETO.finditer(texto or ""):
        if '"accion"' in m.group(0) or "'accion'" in m.group(0):
            candidatos.append(m.group(0))
    for crudo in reversed(candidatos):
        try:
            d = json.loads(crudo)
        except ValueError:
            continue
        if not isinstance(d, dict):
            continue
        accion = _SINONIMOS.get(str(d.get("accion", "")).strip().lower())
        if accion is None:
            continue
        lado = str(d.get("lado", "")).strip().lower()
        if str(d.get("accion", "")).strip().lower() == "comprar":
            lado = "compra"
        elif str(d.get("accion", "")).strip().lower() == "vender":
            lado = "venta"
        ticket = _a_numero(d.get("ticket"))
        return {
            "accion": accion,
            "lado": lado if lado in ("compra", "venta") else None,
            "stop_loss": _a_numero(d.get("stop_loss")),
            "take_profit": _a_numero(d.get("take_profit")),
            "ticket": int(ticket) if ticket is not None else None,
            "resumen": str(d.get("resumen") or "").strip()[:300],
        }
    return {"accion": "esperar", "lado": None, "stop_loss": None, "take_profit": None, "ticket": None,
            "resumen": "No se pudo leer la decisión del análisis; se espera al próximo chequeo.", "invalida": True}
