"""Catálogo de símbolos del terminal (ventana "Comparar" del gráfico), con caché."""
import time

from proveedores.selector_mt5 import mt5  # type: ignore[import-untyped]
from herramientas.puente_mt5 import inicializar_mt5

from .constantes import CANDADO_MT5, TTL_SIMBOLOS

_SIMBOLOS = {"t": 0.0, "datos": []}


def listar_simbolos() -> list:
    """Catálogo de símbolos del terminal para la ventana "Comparar" del gráfico:
    n = nombre, d = descripción, c = categoría (primer tramo de la ruta del símbolo en MT5)."""
    ahora = time.time()
    if _SIMBOLOS["datos"] and ahora - _SIMBOLOS["t"] < TTL_SIMBOLOS:
        return _SIMBOLOS["datos"]
    with CANDADO_MT5:
        inicializar_mt5()
        todos = mt5.symbols_get() or []
    datos = []
    for s in todos:
        ruta = (getattr(s, "path", "") or "").replace("\\", "/")
        datos.append({"n": s.name, "d": getattr(s, "description", "") or "", "c": ruta.split("/")[0] if "/" in ruta else ""})
    datos.sort(key=lambda x: x["n"].lower())
    if datos:
        _SIMBOLOS["t"], _SIMBOLOS["datos"] = ahora, datos
    return datos
