"""Conexión con el terminal de MT5: reintentos con espera, sesión con candado y envoltorio de solo lectura.
El estado de la conexión (último fallo, error, ruta) vive aquí, junto a las funciones que lo modifican."""
from __future__ import annotations

import importlib
import os
import time
from contextlib import contextmanager
from typing import Any, Iterator, NoReturn

from dotenv import load_dotenv

from fuentes.mt5_fuentes.candado import _lock
from fuentes.mt5_fuentes.constantes import _MAX_RUTAS, _REINTENTO_S, _TIMEOUT_MS
from fuentes.mt5_fuentes.errores import ErrorMT5
from fuentes.mt5_fuentes.rutas import rutas_candidatas
from fuentes.mt5_fuentes.solo_lectura import _SoloLectura

# Cargar el .env ANTES de leer PROVEEDOR, para que la decisión no dependa del
# orden de import (si no, podría caer a 'mt5' y abrir el terminal por error).
load_dotenv()

_raw: Any = None
_proxy: _SoloLectura | None = None
_ultimo_fallo = 0.0
_ultimo_error = ""
_ruta_conectada: str | None = None

# Proveedor de bajo nivel: con PROVEEDOR=capital se usa el shim de Capital.com
# (mismo que el resto de la app), no el terminal MetaTrader 5.
_ES_CAPITAL = os.getenv("PROVEEDOR", "mt5").strip().lower() == "capital"


def _modulo() -> Any:
    global _raw, _proxy
    if _raw is None:
        if _ES_CAPITAL:
            from proveedores import capital_mt5_compat as _mod
            _raw = _mod
        else:
            try:
                _raw = importlib.import_module("MetaTrader5")
            except ImportError as e:
                raise ErrorMT5("Falta la librería MetaTrader5: pip install -U MetaTrader5") from e
        _proxy = _SoloLectura(_raw)
    return _raw


def _fallar(mensaje: str) -> NoReturn:
    global _ultimo_fallo, _ultimo_error
    _ultimo_fallo = time.time()
    _ultimo_error = mensaje
    raise ErrorMT5(mensaje)


def _espera_restante() -> float:
    if not _ultimo_error:
        return 0.0
    return max(0.0, _REINTENTO_S - (time.time() - _ultimo_fallo))


def _conectar(raw: Any) -> None:
    global _ruta_conectada, _ultimo_error
    # Salvaguarda: bajo Capital NUNCA se abre el terminal MetaTrader 5.
    if _ES_CAPITAL:
        _fallar("PROVEEDOR=capital: no se abre el terminal MT5 (se usa la API REST).")
    rutas = rutas_candidatas()
    if not rutas:
        _fallar("No se encontró ningún terminal64.exe de MT5.")

    errores: list[str] = []
    for ruta in rutas[:_MAX_RUTAS]:
        if raw.initialize(path=ruta, timeout=_TIMEOUT_MS):
            _ruta_conectada = ruta
            break
        errores.append(f"{ruta} → {raw.last_error()}")
    else:
        _fallar("No se pudo conectar con MT5: " + " | ".join(errores))

    _ultimo_error = ""


def asegurar_conexion() -> _SoloLectura:
    raw = _modulo()
    if raw.terminal_info() is None:
        if _ES_CAPITAL:
            # El shim no usa rutas de terminal: abre/renueva la sesión REST.
            if not raw.initialize():
                _fallar("No se pudo conectar con Capital.com (revisa las credenciales del .env).")
        else:
            espera = _espera_restante()
            if espera > 0:
                raise ErrorMT5(f"{_ultimo_error} (reintento en {espera:.0f} s)")
            _conectar(raw)
    if _proxy is None:
        raise ErrorMT5("Módulo MT5 no inicializado.")
    return _proxy


@contextmanager
def _sesion() -> Iterator[_SoloLectura]:
    lock = _lock()
    if _espera_restante() > 0:
        if not lock.acquire(blocking=False):
            raise ErrorMT5(f"{_ultimo_error} (reintento en {_espera_restante():.0f} s)")
    else:
        lock.acquire()
    try:
        yield asegurar_conexion()
    finally:
        lock.release()
