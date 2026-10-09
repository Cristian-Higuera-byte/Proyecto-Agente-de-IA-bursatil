"""Paquete de herramientas del agente.

Cada módulo nuevo de herramientas (mt5, yfinance, investing, conocimiento, analisis, simulacion, diagnostico, graficos, tablas...)
se importa aquí para que sus funciones queden registradas al arrancar el agente.
"""

from importlib import import_module
from types import ModuleType

utilidades: ModuleType = import_module(".utilidades", __name__)
yfinance_tools: ModuleType = import_module(".yfinance_tools", __name__)
investing_tools: ModuleType = import_module(".investing_tools", __name__)
mt5_tools: ModuleType = import_module(".mt5_tools", __name__)
conocimiento: ModuleType = import_module(".conocimiento", __name__)
analisis_tools: ModuleType = import_module(".analisis_tools", __name__)
simulacion_tools: ModuleType = import_module(".simulacion_tools", __name__)
diagnostico_tools: ModuleType = import_module(".diagnostico_tools", __name__)
graficos_tools: ModuleType = import_module(".graficos_tools", __name__)
tablas_tools: ModuleType = import_module(".tablas_tools", __name__)
cuantitativo_tools: ModuleType = import_module(".cuantitativo_tools", __name__)
gestion_riesgo_tools: ModuleType = import_module(".gestion_riesgo_tools", __name__)
estructura_mercado_tools: ModuleType = import_module(".estructura_mercado_tools", __name__)
macro_eventos_tools: ModuleType = import_module(".macro_eventos_tools", __name__)
sentimiento_tools: ModuleType = import_module(".sentimiento_tools", __name__)
ordenes_tools: ModuleType = import_module(".ordenes_tools", __name__)


__all__ = [
    "utilidades",
    "yfinance_tools",
    "investing_tools",
    "mt5_tools",
    "conocimiento",
    "analisis_tools",
    "simulacion_tools",
    "diagnostico_tools",
    "graficos_tools",
    "tablas_tools",
    "cuantitativo_tools",
    "gestion_riesgo_tools",
    "estructura_mercado_tools",
    "macro_eventos_tools",
    "sentimiento_tools",
    "ordenes_tools",
]