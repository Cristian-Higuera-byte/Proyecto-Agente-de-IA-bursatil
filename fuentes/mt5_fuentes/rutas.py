"""Rutas candidatas del terminal64.exe de MT5 (MT5_PATH del .env, terminal abierto, carpetas típicas)."""
from __future__ import annotations

import glob
import os
import subprocess
import time

from fuentes.mt5_fuentes.constantes import _TTL_RUTAS_S


def _terminal_en_ejecucion() -> list[str]:
    try:
        salida = subprocess.run(
            [
                "powershell", "-NoProfile", "-Command",
                "Get-Process terminal64 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Path",
            ],
            capture_output=True, text=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout
        return [l.strip() for l in salida.splitlines() if l.strip().lower().endswith("terminal64.exe")]
    except Exception:
        return []


_rutas_cache: tuple[float, list[str]] | None = None


def rutas_candidatas(refrescar: bool = False) -> list[str]:
    global _rutas_cache
    ahora = time.monotonic()
    if _rutas_cache is not None and not refrescar and ahora - _rutas_cache[0] < _TTL_RUTAS_S:
        return list(_rutas_cache[1])

    rutas: list[str] = []
    en_env = os.getenv("MT5_PATH", "").strip().strip('"')
    if en_env and os.path.isfile(en_env):
        rutas.append(en_env)
    rutas += _terminal_en_ejecucion()
    for base in (
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        os.path.expandvars(r"%APPDATA%\MetaQuotes\Terminal"),
    ):
        rutas += glob.glob(os.path.join(base, "*", "terminal64.exe"))
    vistas: set[str] = set()
    unicas: list[str] = []
    for r in rutas:
        k = os.path.normcase(os.path.abspath(r))
        if k not in vistas and os.path.isfile(r):
            vistas.add(k)
            unicas.append(r)
    if unicas:
        _rutas_cache = (ahora, unicas)
    return unicas
