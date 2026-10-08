"""
cerradas_store.py
-----------------
Persistencia de las TARJETAS DE POSICIONES CERRADAS de la Cartera.

Viven en `st.session_state`, que se reinicia al recargar la página (F5 = sesión
nueva). Para que las tarjetas sobrevivan al F5 mientras el navegador está abierto,
se respaldan en `data/cerradas.json` (escritura atómica, como `trailing.json`).

Es un archivo único (demo de una sola cuenta MT5). Si en el futuro hay varias
cuentas/usuarios, convendría keyearlo por usuario.
"""
import json
import os
import tempfile
import threading

_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_RUTA = os.path.join(_DIR, "cerradas.json")
_LOCK = threading.Lock()


def leer() -> list:
    """Lista de tarjetas cerradas (más recientes primero)."""
    try:
        with open(_RUTA, "r", encoding="utf-8") as f:
            datos = json.load(f)
        return datos if isinstance(datos, list) else []
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def guardar(lista: list) -> None:
    with _LOCK:
        os.makedirs(_DIR, exist_ok=True)
        tmp = tempfile.NamedTemporaryFile("w", delete=False, dir=_DIR, encoding="utf-8")
        try:
            json.dump(list(lista), tmp)
            tmp.flush()
            os.fsync(tmp.fileno())
        finally:
            tmp.close()
        os.replace(tmp.name, _RUTA)   # atómico
