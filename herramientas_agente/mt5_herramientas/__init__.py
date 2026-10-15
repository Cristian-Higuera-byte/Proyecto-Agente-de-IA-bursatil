"""Herramientas del agente basadas en MetaTrader 5 (terminal de XM) — SOLO LECTURA.

Archivos: herramientas.py (registro de las herramientas), auxiliares.py, esquemas.json.
"""
from herramientas_agente.mt5_herramientas.auxiliares import _SIMBOLO
from herramientas_agente.mt5_herramientas.herramientas import (
    mt5_buscar_simbolos,
    mt5_precio,
    mt5_velas,
    mt5_cuenta,
    mt5_posiciones,
    mt5_ordenes_pendientes,
    mt5_historial_operaciones,
)
