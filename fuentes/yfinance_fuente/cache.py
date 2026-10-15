"""Caché en memoria con vencimiento para no saturar las peticiones a Yahoo."""
from __future__ import annotations

import time
from typing import Any, Callable

# ──────────────────────────────────────────────────────────────
# Utilidades internas
# ──────────────────────────────────────────────────────────────
_CACHE: dict[str, tuple[float, Any]] = {}


def _cacheado(clave: str, ttl: float, fn: Callable[[], Any]) -> Any:
    """Cache en memoria con vencimiento: evita golpear a Yahoo con consultas repetidas."""
    ahora = time.monotonic()
    guardado = _CACHE.get(clave)
    if guardado and ahora - guardado[0] < ttl:
        return guardado[1]
    valor = fn()  # si lanza excepción, no se cachea
    _CACHE[clave] = (ahora, valor)
    return valor
