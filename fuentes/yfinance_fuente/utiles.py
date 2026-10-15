"""Utilidades de normalización: símbolos, números, campos, fechas."""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any


def _simbolo(texto: str) -> str:
    s = (texto or "").strip().upper()
    if not s:
        raise ValueError("Falta el símbolo.")
    return s


def _num(valor: Any, decimales: int = 4) -> float | None:
    """Convierte a float JSON-seguro (NaN/inf/None -> None)."""
    try:
        f = float(valor)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return round(f, decimales)


def _entero(valor: Any) -> int | None:
    n = _num(valor, 0)
    return int(n) if n is not None else None


def _leer(obj: Any, nombre: str, texto: bool = False) -> Any:
    try:
        v = getattr(obj, nombre)
    except Exception:  # noqa: BLE001 - fast_info lanza KeyError/AttributeError si falta
        return None
    return v if texto else _num(v)


def _sin_nulos(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


def _validar_fecha(texto: str, campo: str) -> str:
    try:
        datetime.strptime(texto, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"'{campo}' debe tener formato AAAA-MM-DD (recibido: {texto!r}).") from None
    return texto


def _fmt_fecha(ts: Any, intradia: bool) -> str:
    return ts.strftime("%Y-%m-%d %H:%M" if intradia else "%Y-%m-%d")
