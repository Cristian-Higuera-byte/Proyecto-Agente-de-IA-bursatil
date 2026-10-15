"""Módulo de análisis cuantitativo, riesgo estadístico y simulación para el agente.

NOMBRE DEL ARCHIVO: herramientas_agente/cuantitativo_herramientas

Archivos: herramientas.py (registro de las herramientas), auxiliares.py, esquemas.json.
"""
from herramientas_agente.cuantitativo_herramientas.auxiliares import (
    _mapear_simbolo_yf,
    _obtener_retornos_historicos,
)
from herramientas_agente.cuantitativo_herramientas.herramientas import (
    calcular_matriz_correlacion,
    simular_monte_carlo_cartera,
    evaluar_metricas_rendimiento,
)
