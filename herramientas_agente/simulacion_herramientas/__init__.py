"""Módulo de herramientas de simulación y análisis de escenarios 'What-If' para el agente.

NOMBRE DEL ARCHIVO: herramientas_agente/simulacion_herramientas

Archivos: herramientas.py (registro de las herramientas), auxiliares.py, esquemas.json.
"""
from herramientas_agente.simulacion_herramientas.auxiliares import (
    ELASTICIDAD_CRUZADA,
    _normalizar_simbolo,
    _estimar_tamano_contrato,
)
from herramientas_agente.simulacion_herramientas.herramientas import simular_escenario_cartera
