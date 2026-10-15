"""Paquete de herramientas del agente (antes `herramientas/`).

Cada módulo nuevo de herramientas (mt5, yfinance, investing, conocimiento, analisis, simulacion, diagnostico, graficos, tablas...)
se importa aquí para que sus funciones queden registradas al arrancar el agente.
"""

from importlib import import_module
from types import ModuleType

utilidades: ModuleType = import_module(".utilidades", __name__)
yfinance_herramientas: ModuleType = import_module(".yfinance_herramientas", __name__)
investing_herramientas: ModuleType = import_module(".investing_herramientas", __name__)
mt5_herramientas: ModuleType = import_module(".mt5_herramientas", __name__)
conocimiento: ModuleType = import_module(".conocimiento", __name__)
analisis_herramientas: ModuleType = import_module(".analisis_herramientas", __name__)
simulacion_herramientas: ModuleType = import_module(".simulacion_herramientas", __name__)
diagnostico_herramientas: ModuleType = import_module(".diagnostico_herramientas", __name__)
graficos_herramientas: ModuleType = import_module(".graficos_herramientas", __name__)
tablas_herramientas: ModuleType = import_module(".tablas_herramientas", __name__)
cuantitativo_herramientas: ModuleType = import_module(".cuantitativo_herramientas", __name__)
gestion_riesgo_herramientas: ModuleType = import_module(".gestion_riesgo_herramientas", __name__)
estructura_mercado_herramientas: ModuleType = import_module(".estructura_mercado_herramientas", __name__)
macro_eventos_herramientas: ModuleType = import_module(".macro_eventos_herramientas", __name__)
sentimiento_herramientas: ModuleType = import_module(".sentimiento_herramientas", __name__)
ordenes_herramientas: ModuleType = import_module(".ordenes_herramientas", __name__)
informe_cartera_herramientas: ModuleType = import_module(".informe_cartera_herramientas", __name__)

__all__ = [
    "utilidades",
    "yfinance_herramientas",
    "investing_herramientas",
    "mt5_herramientas",
    "conocimiento",
    "analisis_herramientas",
    "simulacion_herramientas",
    "diagnostico_herramientas",
    "graficos_herramientas",
    "tablas_herramientas",
    "cuantitativo_herramientas",
    "gestion_riesgo_herramientas",
    "estructura_mercado_herramientas",
    "macro_eventos_herramientas",
    "sentimiento_herramientas",
    "ordenes_herramientas",
    "informe_cartera_herramientas",
]
