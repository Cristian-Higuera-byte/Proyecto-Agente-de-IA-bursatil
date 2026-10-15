"""Utilidades de las consultas: números, fechas UTC, resolución de símbolos (alias) y símbolo temporal."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from fuentes.mt5_fuentes.constantes import _ALIAS
from fuentes.mt5_fuentes.errores import ErrorMT5


def _num(v: Any, dec: int = 5) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return round(f, dec)


def _nivel(v: Any) -> float | None:
    return _num(v) if v else None


def _hora_utc(ts: Any, mt5: Any) -> str:
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S") + " UTC"


def _fecha_utc(texto: str, campo: str) -> datetime:
    try:
        return datetime.strptime(texto, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise ErrorMT5(f"'{campo}' debe tener formato AAAA-MM-DD.") from None


def _como_tupla(mt5: Any, resultado: Any, accion: str) -> Any:
    if resultado is None:
        err = mt5.last_error()
        if err and err[0] != getattr(mt5, "RES_S_OK", 1):
            raise ErrorMT5(f"MT5 falló al {accion}: {err}")
        return ()
    return resultado


def _resolver(mt5: Any, texto: str) -> str:
    bruto = (texto or "").strip().upper()
    if not bruto:
        raise ErrorMT5("Falta el símbolo.")
    info = mt5.symbol_info(bruto)
    if info is not None:
        return bruto
    for alias in _ALIAS.get(bruto, []):
        if mt5.symbol_info(alias) is not None:
            return alias
    return bruto


@contextmanager
def _simbolo_temporal(mt5: Any, simbolo: str) -> Iterator[Any]:
    info = mt5.symbol_info(simbolo)
    if info is None:
        raise ErrorMT5(f"El símbolo '{simbolo}' no existe en MT5.")
    estaba_visible = bool(info.visible)
    if not estaba_visible:
        mt5.symbol_select(simbolo, True)
    try:
        yield info
    finally:
        if not estaba_visible:
            try:
                mt5.symbol_select(simbolo, False)
            except Exception:
                pass


def _tamano_pip(info: Any) -> float:
    """Tamaño de un 'pip' en precio: 10 puntos en símbolos de 3 o 5 decimales; el punto en el resto."""
    punto = float(getattr(info, "point", 0) or 0)
    return punto * 10 if getattr(info, "digits", 0) in (3, 5) else punto


def _tipo_orden(mt5: Any, tipo: str) -> int:
    return mt5.ORDER_TYPE_BUY if str(tipo).upper() in ("COMPRA", "BUY") else mt5.ORDER_TYPE_SELL
