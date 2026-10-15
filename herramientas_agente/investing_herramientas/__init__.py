"""Herramientas del agente basadas en Investing.com (en español).

Todas llevan el prefijo inv_ para que el modelo distinga claramente de qué
fuente proviene cada noticia. La lógica real vive en fuentes/investing_fuente.py.

Archivos: herramientas.py (registro de las herramientas), esquemas.json.
"""
from herramientas_agente.investing_herramientas.herramientas import inv_noticias, inv_buscar_noticias
