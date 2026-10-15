"""Módulo de riesgo macroeconómico por noticias.

NOMBRE DEL ARCHIVO: herramientas_agente/macro_eventos_herramientas

No hay una fuente de calendario económico con horas exactas conectada. Esta herramienta NO inventa
eventos: revisa los titulares reales y recientes de Investing.com y señala los que hablan de eventos
de alto impacto (nóminas, inflación, bancos centrales, PIB...). Es una señal por titulares, no un
calendario: no sirve para saber a qué hora sale un dato.

Archivos: herramientas.py (registro de las herramientas), auxiliares.py, esquemas.json, datos.json.
"""
from herramientas_agente.macro_eventos_herramientas.auxiliares import CATEGORIAS, _EVENTOS, _DIVISAS
from herramientas_agente.macro_eventos_herramientas.herramientas import evaluar_riesgo_noticias_proximas
