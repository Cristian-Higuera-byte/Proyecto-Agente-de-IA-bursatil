"""Fuente de datos: Yahoo Finance (librería yfinance).

Esta capa solo sabe OBTENER y NORMALIZAR datos. No conoce al modelo ni a las
herramientas: devuelve diccionarios/listas simples y lanza ValueError con un
mensaje claro cuando algo no existe (el registro de herramientas se lo pasa
al modelo para que pueda corregir el símbolo o explicárselo al usuario).

Símbolos de Yahoo:
    acciones  AAPL, MSFT        forex      EURUSD=X, USDCLP=X
    índices   ^GSPC, ^IXIC      cripto     BTC-USD
    materias primas  GC=F (oro), CL=F (petróleo)

Los datos son gratuitos y pueden llegar con retraso (hasta ~15 min según el mercado).

Prueba rápida (desde la raíz del proyecto):  python -m fuentes.yfinance_fuente

Archivos: constantes.py + datos.json, cache.py, utiles.py, mercado.py, fundamentales.py, noticias.py y __main__.py."""
from fuentes.yfinance_fuente.constantes import (
    AVISO_RETRASO,
    INTERVALOS,
    PERIODOS,
    _CAMPOS_NUM,
    _CAMPOS_TEXTO,
    _ESTADOS,
)  # noqa: F401
from fuentes.yfinance_fuente.cache import (
    _CACHE,
    _cacheado,
)  # noqa: F401
from fuentes.yfinance_fuente.utiles import (
    _entero,
    _fmt_fecha,
    _leer,
    _num,
    _simbolo,
    _sin_nulos,
    _validar_fecha,
)  # noqa: F401
from fuentes.yfinance_fuente.mercado import (
    buscar,
    cotizacion,
    historico,
)  # noqa: F401
from fuentes.yfinance_fuente.fundamentales import (
    estados_financieros,
    fundamentales,
)  # noqa: F401
from fuentes.yfinance_fuente.noticias import (
    consenso_analistas,
    noticias,
    _normalizar_noticia,
)  # noqa: F401
