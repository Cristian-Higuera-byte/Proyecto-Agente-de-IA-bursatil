"""Registro de turnos y agentes por usuario (un turno a la vez por usuario) y API que usa la interfaz."""
from __future__ import annotations

import threading
from typing import Any

from nucleo_agente import notificaciones
from nucleo_agente.turnos.hilo import _correr
from nucleo_agente.turnos.turno import Turno

_LOCK = threading.Lock()
_TURNOS: dict[str, Turno] = {}    # último turno de cada usuario
_AGENTES: dict[str, Any] = {}     # un Agente por usuario (sobrevive a recargas de la página)


# ── API ───────────────────────────────────────────────────────────────────────────────
def agente_de(usuario_id: str) -> Any:
    with _LOCK:
        return _AGENTES.get(usuario_id)


def registrar_agente(usuario_id: str, agente: Any) -> None:
    with _LOCK:
        _AGENTES[usuario_id] = agente


def turno_de(usuario_id: str) -> Turno | None:
    with _LOCK:
        return _TURNOS.get(usuario_id)


def hay_turno_en_curso(usuario_id: str) -> bool:
    t = turno_de(usuario_id)
    return t is not None and not t.terminado


def iniciar(usuario_id: str, agente: Any, prompt: str) -> Turno | None:
    """Lanza el turno en segundo plano. Devuelve None si ya hay uno en curso para ese usuario."""
    with _LOCK:
        actual = _TURNOS.get(usuario_id)
        if actual is not None and not actual.terminado:
            return None
        turno = Turno(usuario_id=usuario_id, prompt=prompt)
        _TURNOS[usuario_id] = turno
    threading.Thread(target=_correr, args=(turno, agente), name=f"turno-{turno.id}", daemon=True).start()
    return turno


def cancelar(usuario_id: str) -> bool:
    """Pide detener el turno en curso del usuario. True si había uno al que pedírselo."""
    with _LOCK:
        t = _TURNOS.get(usuario_id)
        if t is None or t.terminado:
            return False
        t.cancelar_solicitado = True
        t.fase = "Deteniendo…"
        return True


def recoger(usuario_id: str, turno_id: str) -> None:
    """La interfaz ya mostró el resultado: se marca como incorporado y se leen sus avisos."""
    with _LOCK:
        t = _TURNOS.get(usuario_id)
        if t is not None and t.id == turno_id:
            t.recogido = True
    notificaciones.marcar_leidas(usuario_id, ref=turno_id)
