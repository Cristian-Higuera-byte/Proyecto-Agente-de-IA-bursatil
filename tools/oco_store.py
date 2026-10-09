"""
oco_store.py
------------
Almacén COMPARTIDO de los pares OCO (One-Cancels-the-Other).

Un OCO son DOS órdenes pendientes vinculadas: cuando una se EJECUTA, la otra se
cancela sola. MT5 no tiene OCO nativo (igual que el trailing, la lógica vive en
el cliente): el ticket de órdenes (`components/order_panel.py`, proceso de
Streamlit) registra el par aquí al colocar las dos patas, y el motor de
`servidor_datos.py` (otro proceso) lo vigila y cancela la pata sobrante.

Ambos procesos comparten el archivo `data/oco.json`, como el resto de
`data/*.json`. La escritura es atómica (`os.replace`) para que el motor nunca
lea un archivo a medias.

Formato de `data/oco.json`:
    { "<par_id>": {"a": <ticketA>, "b": <ticketB>, "symbol": "<real>", "ts": <epoch>} }

- `par_id`: "<a>-<b>" (los dos tickets ordenados), identifica el par.
- `a` / `b`: los tickets de las dos órdenes pendientes de MT5 que forman el par.
- `symbol`: nombre real del símbolo en el terminal (informativo / para la UI).
- `ts`: epoch en que se creó el par (informativo).

Semántica OCO (la aplica el motor): si una pata SE EJECUTA (pasa a posición), se
cancela la otra. Si el usuario cancela una pata a mano, solo se rompe el vínculo
(la otra queda como orden pendiente normal).
"""
import json
import os
import tempfile
import threading
import time

_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_RUTA = os.path.join(_DIR, "oco.json")
_LOCK = threading.Lock()


def _par_id(a: int, b: int) -> str:
    x, y = sorted((int(a), int(b)))
    return f"{x}-{y}"


def _leer_crudo() -> dict:
    try:
        with open(_RUTA, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def leer() -> dict:
    """Devuelve {par_id(str): {"a": int, "b": int, "symbol": str, "ts": float}}."""
    out = {}
    for k, v in _leer_crudo().items():
        try:
            out[str(k)] = {"a": int(v["a"]), "b": int(v["b"]),
                           "symbol": str(v.get("symbol", "")), "ts": float(v.get("ts", 0.0))}
        except (ValueError, TypeError, KeyError, AttributeError):
            continue
    return out


def tickets_en_oco() -> set:
    """Conjunto de todos los tickets que participan en algún par OCO (para la UI/feed)."""
    s = set()
    for v in leer().values():
        s.add(v["a"])
        s.add(v["b"])
    return s


def _guardar(d: dict) -> None:
    os.makedirs(_DIR, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile("w", delete=False, dir=_DIR, encoding="utf-8")
    try:
        json.dump(d, tmp)
        tmp.flush()
        os.fsync(tmp.fileno())
    finally:
        tmp.close()
    os.replace(tmp.name, _RUTA)   # atómico: el otro proceso nunca ve un archivo a medias


def fijar(a: int, b: int, symbol: str = "") -> str:
    """Vincula dos órdenes pendientes como un par OCO. Devuelve el par_id."""
    with _LOCK:
        d = leer()
        pid = _par_id(a, b)
        d[pid] = {"a": int(a), "b": int(b), "symbol": str(symbol or ""), "ts": time.time()}
        _guardar(d)
        return pid


def quitar_par(par_id: str) -> None:
    """Elimina un par OCO por su id (si existía)."""
    with _LOCK:
        d = leer()
        if str(par_id) in d:
            d.pop(str(par_id))
            _guardar(d)


def quitar_ticket(ticket: int) -> None:
    """Elimina cualquier par que contenga este ticket (si existía)."""
    with _LOCK:
        d = leer()
        tk = int(ticket)
        cambio = False
        for pid in [p for p, v in d.items() if v["a"] == tk or v["b"] == tk]:
            d.pop(pid, None)
            cambio = True
        if cambio:
            _guardar(d)


def mtime() -> float:
    """Marca de tiempo del archivo (para recargar solo cuando cambió)."""
    try:
        return os.path.getmtime(_RUTA)
    except OSError:
        return 0.0
