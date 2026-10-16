# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ------------------------------------- INICIO Piña y Jara datos .PY ------------------------------------
# -------------------------------------------------------------------------------------------------------

"""Fuentes RSS y parámetros del panel de noticias (viven en fuentes.json).

Separa la configuración (URLs y tamaños de paginación) del código que lee los feeds, de modo que se pueda
cambiar sin tocar la lógica.
"""
from pathlib import Path

from componentes_plataforma._estaticos import datos_json

# Contenido completo de fuentes.json
_D = datos_json(Path(__file__).parent / "fuentes.json")

# URLs de los RSS que alimentan la noticia principal y el carrusel
FUENTES = list(_D["fuentes"])
FUENTES_MAS = list(_D["fuentes_mas"])      # categorías adicionales: Cripto, Forex y Economía
# Imagen de respaldo para las noticias que no traen foto
PLACEHOLDER = _D["placeholder"]
# Noticias por página del carrusel (también las columnas que se dibujan)
POR_PAGINA = _D["por_pagina"]
# Máximo de noticias del carrusel (sin contar la principal)
MAX_CARRUSEL = _D["max_carrusel"]


# -------------------------------------------------------------------------------------------------------
# -------------------------------------- FIN Piña y Jara datos .PY --------------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
