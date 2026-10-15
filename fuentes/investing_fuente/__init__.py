"""Fuente de datos: Investing.com (en español).

Esta capa solo se encarga de OBTENER y NORMALIZAR noticias macroeconómicas y
de mercados. No conoce al modelo ni a las herramientas: devuelve listas/dict
simples y lanza ErrorInvesting con un mensaje claro si ocurre algún fallo.

Feeds disponibles (Investing.com España):
    general, mercados, forex, acciones, cripto, economia

Prueba rápida (desde la raíz del proyecto):  python -m fuentes.investing_fuente

Archivos: constantes.py + datos.json, errores.py, cache.py, utiles.py, noticias.py y __main__.py."""
from fuentes.investing_fuente.constantes import (
    AVISO_FUENTE,
    FEEDS,
    HEADERS,
)  # noqa: F401
from fuentes.investing_fuente.errores import (
    ErrorInvesting,
)  # noqa: F401
from fuentes.investing_fuente.cache import (
    _CACHE,
    _cacheado,
)  # noqa: F401
from fuentes.investing_fuente.utiles import (
    _limpiar_html,
    _sin_nulos,
)  # noqa: F401
from fuentes.investing_fuente.noticias import (
    buscar_noticias,
    noticias,
)  # noqa: F401
