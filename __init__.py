"""Módulo de conexión con fuentes de datos externas."""

from importlib import import_module
from types import ModuleType

mt5_fuentes: ModuleType = import_module(".mt5_fuentes", __name__)
yfinance_fuente: ModuleType = import_module(".yfinance_fuente", __name__)
investing_fuente: ModuleType = import_module(".investing_fuente", __name__)

__all__ = [
    "mt5_fuentes",
    "yfinance_fuente",
    "investing_fuente",
]