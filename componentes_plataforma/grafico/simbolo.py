"""Datos de un símbolo que necesita el gráfico: nombre limpio, decimales y tamaño del pip."""
from __future__ import annotations

from typing import Tuple

from proveedores.selector_mt5 import mt5  # type: ignore[import-untyped]

from herramientas.puente_mt5 import MT5_LOCK, resolver_simbolo


def limpiar_simbolo(valor: str) -> str:
    """Quita los puntos suspensivos con que la lista de activos abrevia el símbolo."""
    return valor.replace("...", "").replace("…", "").strip()


def info_simbolo(simbolo: str) -> Tuple[int, float]:
    """
    Devuelve (decimales, tamaño_del_pip) del símbolo según MT5.
    El pip es 0.0 si el activo no es forex.
    """
    digits = 5
    pip = 0.0
    try:
        real = resolver_simbolo(simbolo)   # el nombre que ve el usuario puede no ser el del bróker
        with MT5_LOCK:                     # la API de MT5 no es segura entre hilos
            mt5.symbol_select(real, True)
            info = mt5.symbol_info(real)
        if info is not None:
            digits = int(info.digits)
            es_forex = info.trade_calc_mode == getattr(mt5, "SYMBOL_CALC_MODE_FOREX", 0)
            if es_forex:
                pip = float(info.point) * (10 if digits in (3, 5) else 1)
    except Exception:
        pass
    return digits, pip
