"""
equity_store.py
---------------
Registro histórico del EQUITY de la cuenta a lo largo del tiempo (snapshots).

¿Por qué existe? MT5 entrega el equity ACTUAL (`account_info().equity`) y el
historial de operaciones CERRADAS (de ahí se reconstruye la curva de *balance*),
pero NO guarda el histórico del equity segundo a segundo. El drawdown REAL —el que
incluye lo que sufre la cuenta con posiciones abiertas— solo se puede calcular si
alguien va anotando el equity en el tiempo. Eso hace este módulo: `servidor_datos.py`
llama a `registrar(...)` periódicamente y la vista Resumen lee `serie(...)`.

  >>> drawdown de equity (real)  ≠  drawdown de balance (solo cambia en cierres)

------------------------------------------------------------------------------
NOTA PARA EL FUTURO (lanzamiento / multiusuario) — leer antes de escalar:
------------------------------------------------------------------------------
Esta implementación es MONO-USUARIO y LOCAL (un archivo `data/equity.json` para la
única cuenta conectada en el terminal de esta máquina). Es correcta para la demo y
para un solo trader, PERO al lanzar la app con varios usuarios hay que mover el
almacenamiento a una base por usuario (p. ej. Supabase, que el proyecto ya usa):

    tabla equity_snapshots(user_id, ts, equity, balance)   -- índice (user_id, ts)

La CLAVE del diseño: toda la app habla con este módulo por su interfaz
(`registrar` / `serie`), nunca con el archivo directamente. Por eso migrar a
Supabase el día del lanzamiento = reescribir SOLO este archivo (mismas firmas),
sin tocar `servidor_datos.py`, `portafolio_stats.py` ni la UI. La lógica del
drawdown, la curva y las tarjetas se reaprovechan intactas. Lo único que no se
puede recuperar hacia atrás es la serie ya acumulada en la demo (ese dato nunca
existió para un usuario real): la curva de equity de cada usuario empieza a
construirse desde que su cuenta queda conectada.
------------------------------------------------------------------------------

Formato del archivo: {"puntos": [[ts, equity, balance], ...]} (ts = epoch, float).
Escritura atómica con os.replace (igual que oco_store / trailing_store).
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time

_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_RUTA = os.path.join(_DIR, "equity.json")

_LOCK = threading.Lock()         # serializa lecturas/escrituras dentro del proceso
MAX_PUNTOS = 40_000              # ~4 semanas a 1 punto/min; se recorta el más antiguo
MIN_INTERVALO = 55.0            # s mínimos entre snapshots (lo controla también el motor)

_ultimo_ts = 0.0                # último snapshot escrito en ESTA ejecución (anti-spam)


def leer() -> list:
    """Devuelve la serie completa [[ts, equity, balance], ...] (vieja → nueva)."""
    try:
        with _LOCK, open(_RUTA, "r", encoding="utf-8") as f:
            datos = json.load(f)
        return list(datos.get("puntos", []))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def serie(desde: float | None = None) -> list:
    """Serie de snapshots, opcionalmente recortada a ts >= `desde` (epoch)."""
    pts = leer()
    if desde is not None:
        pts = [p for p in pts if p and p[0] >= desde]
    return pts


def registrar(equity: float, balance: float, ts: float | None = None,
              min_intervalo: float = MIN_INTERVALO) -> bool:
    """Añade un snapshot si pasó `min_intervalo` desde el anterior. Devuelve True
    si escribió. Pensado para llamarse en el bucle del motor sin saturar el disco."""
    global _ultimo_ts
    ahora = ts if ts is not None else time.time()
    if ahora - _ultimo_ts < min_intervalo:
        return False
    try:
        eq = round(float(equity), 2)
        bal = round(float(balance), 2)
    except (TypeError, ValueError):
        return False

    with _LOCK:
        pts = []
        try:
            with open(_RUTA, "r", encoding="utf-8") as f:
                pts = json.load(f).get("puntos", [])
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pts = []
        pts.append([round(ahora, 1), eq, bal])
        if len(pts) > MAX_PUNTOS:
            pts = pts[-MAX_PUNTOS:]
        try:
            os.makedirs(_DIR, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=_DIR, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"puntos": pts}, f)
            os.replace(tmp, _RUTA)          # atómico
        except OSError:
            return False
    _ultimo_ts = ahora
    return True


def mtime() -> float:
    try:
        return os.path.getmtime(_RUTA)
    except OSError:
        return -1.0
