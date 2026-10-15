"""
almacen_diario.py
----------------
Datos del Trading Journal que MT5 NO guarda: notas del usuario por operación
(estrategia, emoción/razón) y el "plan" de la orden al abrir (entrada, SL, TP),
necesario para el R/R planificado. Clave = `position_id` de MT5 (la misma con la
que estadisticas_diario empareja los deals), para que notas y plan se peguen a su operación.

------------------------------------------------------------------------------
NOTA PARA EL FUTURO (lanzamiento / multiusuario) — igual que almacen_capital:
------------------------------------------------------------------------------
Hoy es un archivo local `data/journal.json` para la única cuenta del terminal. Al
lanzar con varios usuarios, mover a Supabase por usuario:
    tabla journal(user_id, position_id, estrategia, emocion, razon,
                  plan_entrada, plan_sl, plan_tp, plan_tipo, plan_vol, ts)
    PK (user_id, position_id)
Toda la app habla con este módulo por su interfaz (`obtener`/`guardar_notas`/
`guardar_plan`), nunca con el archivo → migrar = reescribir SOLO este archivo
(mismas firmas), sin tocar estadisticas_diario, el bridge ni la UI. Ver también
[[drawdown-equity-multiusuario]] (mismo patrón con almacen_capital).
------------------------------------------------------------------------------

Formato: {"<position_id>": {"estrategia","emocion","razon","plan":{...},"ts"}}.
Escritura atómica (os.replace), como almacen_oco / almacen_stop_dinamico / almacen_capital.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time

_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_RUTA = os.path.join(_DIR, "journal.json")
_LOCK = threading.Lock()


def leer() -> dict:
    try:
        with _LOCK, open(_RUTA, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def obtener(pos_id) -> dict:
    return leer().get(str(pos_id), {})


def _escribir(datos: dict) -> bool:
    try:
        os.makedirs(_DIR, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=_DIR, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False)
        os.replace(tmp, _RUTA)
        return True
    except OSError:
        return False


def _merge(pos_id, campos: dict) -> bool:
    with _LOCK:
        datos = {}
        try:
            with open(_RUTA, "r", encoding="utf-8") as f:
                datos = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            datos = {}
        fila = datos.get(str(pos_id), {})
        fila.update(campos)
        fila["ts"] = time.time()
        datos[str(pos_id)] = fila
        return _escribir(datos)


def guardar_notas(pos_id, estrategia: str = "", emocion: str = "", razon: str = "") -> bool:
    """Notas del usuario para una operación (Tanda B)."""
    return _merge(pos_id, {"estrategia": (estrategia or "").strip(),
                           "emocion": (emocion or "").strip(),
                           "razon": (razon or "").strip()})


def guardar_plan(pos_id, entrada: float, sl: float, tp: float,
                 tipo: str = "", symbol: str = "", volumen: float = 0.0) -> bool:
    """Plan de la orden al ABRIR (Tanda C): se usa para el R/R planificado. Lo
    llama el bridge tras ejecutar una orden a mercado con SL/TP. No pisa las notas."""
    return _merge(pos_id, {"plan": {
        "entrada": float(entrada or 0.0), "sl": float(sl or 0.0), "tp": float(tp or 0.0),
        "tipo": tipo, "symbol": symbol, "volumen": float(volumen or 0.0),
    }})


def mtime() -> float:
    try:
        return os.path.getmtime(_RUTA)
    except OSError:
        return -1.0
