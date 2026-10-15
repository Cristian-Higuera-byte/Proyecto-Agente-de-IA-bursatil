"""Aviso en la campana de notificaciones cuando termina un turno."""
from __future__ import annotations

import time

from nucleo_agente import notificaciones
from nucleo_agente.turnos.formato import formatear_duracion
from nucleo_agente.turnos.turno import VISTA_RECIENTE_S, Turno


def _avisar(turno: Turno) -> None:
    """Deja el aviso en la campana. Si el usuario está viendo el chat, nace ya leído."""
    viendo = (time.time() - turno.ui_viva) < VISTA_RECIENTE_S
    pregunta = turno.prompt if len(turno.prompt) <= 80 else turno.prompt[:77] + "…"
    tiempo = formatear_duracion(turno.duracion)
    if turno.error:
        titulo, tipo = "El agente no pudo responder", "error"
    elif turno.hubo_vigilancia:
        titulo, tipo = "El agente preparó una vigilancia automática", "orden"
        pregunta = "Revísala y autorízala en «Órdenes propuestas»"
    elif turno.hubo_orden:
        titulo, tipo = "El agente propuso una orden", "orden"
    else:
        titulo, tipo = "El agente respondió", "agente"
    notificaciones.agregar(
        turno.usuario_id, titulo, f"{pregunta} · {tiempo}", tipo=tipo, ref=turno.id, leida=viendo,
    )
