"""Herramientas del agente basadas en Yahoo Finance.

Todas llevan el prefijo yf_ para que, cuando se sumen las de MT5 e
investing.com, el modelo distinga de qué fuente viene cada dato.
La lógica real vive en fuentes/yfinance_fuente.py; aquí solo se describe
cada herramienta para el modelo.

Archivos: herramientas.py (registro de las herramientas), auxiliares.py, esquemas.json.
"""
from herramientas_agente.yfinance_herramientas.auxiliares import _SIMBOLO
from herramientas_agente.yfinance_herramientas.herramientas import (
    yf_buscar_simbolo,
    yf_cotizacion,
    yf_historico,
    yf_fundamentales,
    yf_estados_financieros,
    yf_noticias,
    yf_consenso_analistas,
)
