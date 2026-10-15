"""Motor en segundo plano: despierta cada pocos segundos y lanza los chequeos que ya tocan."""
from __future__ import annotations

import threading
import time
import traceback

from nucleo_agente import ordenes
from nucleo_agente.vigilancia.caducidad import _caducar_autorizaciones, _caducar_vencidas
from nucleo_agente.vigilancia.chequeo import chequear
from nucleo_agente.vigilancia.configuracion import ESPERA_MOTOR_S, NOMBRE_HILO_MOTOR, PREFIJO_HILO_CHEQUEO
from nucleo_agente.vigilancia.utilidades import _consultar


def _chequeo_en_curso(vid: str) -> bool:
    nombre = f"{PREFIJO_HILO_CHEQUEO}{vid}"
    return any(t.name == nombre and t.is_alive() for t in threading.enumerate())


def _chequear_seguro(vid: str) -> None:
    try:
        chequear(vid)
    except Exception:  # noqa: BLE001
        traceback.print_exc()


def tick(sincrono: bool = False) -> int:
    """Una pasada del motor: caduca lo vencido y lanza los chequeos que ya tocan. Devuelve cuántos lanzó."""
    _caducar_autorizaciones()
    _caducar_vencidas()
    toca = _consultar(
        "SELECT id FROM vigilancias WHERE estado = 'ACTIVA' AND (proximo_chequeo IS NULL OR proximo_chequeo <= ?)",
        (ordenes._ahora(),),
    )
    lanzados = 0
    for fila in toca:
        vid = fila["id"]
        if _chequeo_en_curso(vid):
            continue
        if sincrono:
            _chequear_seguro(vid)
        else:
            threading.Thread(target=_chequear_seguro, args=(vid,), name=f"{PREFIJO_HILO_CHEQUEO}{vid}",
                             daemon=True).start()
        lanzados += 1
    return lanzados


def _bucle() -> None:
    while True:
        try:
            tick()
        except Exception:  # noqa: BLE001
            traceback.print_exc()
        time.sleep(ESPERA_MOTOR_S)


_LOCK_MOTOR = threading.Lock()


def iniciar_motor() -> bool:
    """Arranca el motor si no está ya en marcha (idempotente, también si Streamlit recarga el módulo).
    Devuelve True si lo arrancó ahora."""
    with _LOCK_MOTOR:
        if any(t.name == NOMBRE_HILO_MOTOR and t.is_alive() for t in threading.enumerate()):
            return False
        threading.Thread(target=_bucle, name=NOMBRE_HILO_MOTOR, daemon=True).start()
        return True
