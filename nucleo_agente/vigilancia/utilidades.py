"""Utilidades de la vigilancia: acceso a la base (vía nucleo_agente.ordenes), actualizar, notificar y finalizar."""
from __future__ import annotations

import traceback
from datetime import datetime
from typing import Any

from nucleo_agente import notificaciones, ordenes


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def _a_numero(valor: Any) -> float | None:
    """Los modelos a veces envían números como texto ('1,25'); None si no es un número."""
    if isinstance(valor, bool) or valor is None or valor == "":
        return None
    try:
        return float(str(valor).replace(",", ".")) if isinstance(valor, str) else float(valor)
    except (TypeError, ValueError):
        return None


def _consultar(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    return ordenes._consultar(sql, params)


def _actualizar(vid: str, **campos: Any) -> None:
    if not campos:
        return
    asignaciones = ", ".join(f"{c} = ?" for c in campos)
    ordenes._ejecutar(f"UPDATE vigilancias SET {asignaciones} WHERE id = ?", (*campos.values(), vid))


def obtener(vid: str) -> dict[str, Any] | None:
    filas = _consultar("SELECT * FROM vigilancias WHERE id = ?", (vid,))
    return filas[0] if filas else None


def _notificar(v: dict[str, Any], titulo: str, texto: str, tipo: str = "auto") -> None:
    try:
        notificaciones.agregar(v["usuario_id"], titulo, texto, tipo=tipo, ref=v["id"])
    except Exception:  # noqa: BLE001 - un fallo al avisar nunca debe tumbar el motor
        traceback.print_exc()


def _lado_txt(lado: str) -> str:
    return "Compra" if str(lado).lower() == "compra" else "Venta"


def _finalizar(v: dict[str, Any], estado: str, titulo: str, texto: str, tipo: str = "auto") -> None:
    _actualizar(v["id"], estado=estado, detalle=texto[:300])
    _notificar(v, titulo, texto, tipo=tipo)
