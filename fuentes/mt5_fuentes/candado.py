"""Candado de MT5: se comparte el del bridge del dashboard si existe; si no, uno propio (se decide UNA vez al importar)."""
from __future__ import annotations

import importlib
import os
from typing import Any

import threading

_LOCK_PROPIO = threading.RLock()


def _resolver_lock_compartido() -> Any:
    ruta = os.getenv("MT5_BRIDGE_MODULO", "herramientas.puente_mt5").strip() or "herramientas.puente_mt5"
    try:
        return importlib.import_module(ruta).MT5_LOCK
    except Exception:
        return None


_LOCK_COMPARTIDO: Any = _resolver_lock_compartido()


def _lock() -> Any:
    return _LOCK_COMPARTIDO if _LOCK_COMPARTIDO is not None else _LOCK_PROPIO
