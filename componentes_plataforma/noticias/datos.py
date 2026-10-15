"""Fuentes RSS y parámetros del panel de noticias (viven en fuentes.json)."""
from pathlib import Path

from componentes_plataforma._estaticos import datos_json

_D = datos_json(Path(__file__).parent / "fuentes.json")

FUENTES = list(_D["fuentes"])
FUENTES_MAS = list(_D["fuentes_mas"])      # categorías adicionales: Cripto, Forex y Economía
PLACEHOLDER = _D["placeholder"]
POR_PAGINA = _D["por_pagina"]
MAX_CARRUSEL = _D["max_carrusel"]
