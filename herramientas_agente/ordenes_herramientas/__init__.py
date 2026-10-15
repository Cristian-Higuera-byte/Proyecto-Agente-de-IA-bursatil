"""Herramientas del agente para operar: SOLO proponer y consultar (Fase 1).

NOMBRE DEL ARCHIVO: herramientas_agente/ordenes_herramientas

Ninguna de estas herramientas ejecuta órdenes en MetaTrader 5. Las propuestas quedan
pendientes y el usuario las confirma con un botón en el dashboard (nucleo_agente/ordenes.py).

Archivos: herramientas.py (registro de las herramientas), auxiliares.py, esquemas.json.
"""
from herramientas_agente.ordenes_herramientas.auxiliares import _a_numero
from herramientas_agente.ordenes_herramientas.herramientas import (
    proponer_orden,
    proponer_cierre_posicion,
    ver_posiciones,
    ver_limites_riesgo,
    proponer_vigilancia,
    detener_vigilancia,
    ver_vigilancias,
)
