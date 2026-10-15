"""Caducidad: autorizaciones que vencieron y vigilancias cuyo tiempo terminó."""
from __future__ import annotations

from nucleo_agente import ordenes
from nucleo_agente.vigilancia.configuracion import EXPIRADA
from nucleo_agente.vigilancia.posiciones import _posiciones_de
from nucleo_agente.vigilancia.utilidades import _consultar, _finalizar


def _caducar_autorizaciones() -> None:
    ordenes._ejecutar(
        "UPDATE vigilancias SET estado = 'EXPIRADA', detalle = 'La autorización venció' "
        "WHERE estado = 'PENDIENTE_AUTORIZACION' AND expira_autorizacion <= ?", (ordenes._ahora(),),
    )


def _caducar_vencidas() -> None:
    for v in _consultar("SELECT * FROM vigilancias WHERE estado = 'ACTIVA' AND vence <= ?", (ordenes._ahora(),)):
        extra = " Queda una posición abierta (con su stop loss y take profit)." if _posiciones_de(v) else ""
        _finalizar(v, EXPIRADA, f"Vigilancia terminada · {v['simbolo']}",
                   f"Se cumplió el tiempo de la vigilancia ({v['duracion_horas']:g} h).{extra}")
