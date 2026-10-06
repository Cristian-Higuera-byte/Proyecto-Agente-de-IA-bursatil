"""Herramientas del agente basadas en MetaTrader 5 (terminal de XM) — SOLO LECTURA."""

from fuentes import mt5_fuentes as fuente
from herramientas.base import herramienta

_SIMBOLO = {
    "type": "string",
    "description": (
        "Símbolo tal como lo llama el broker en MT5 (EURUSD, GOLD, US500...). También acepta "
        "formatos de Yahoo (EURUSD=X, GC=F, ^GSPC) y 'EUR/USD'."
    ),
}

_SIMBOLO_OPCIONAL = {
    "type": "string",
    "description": "Símbolo para filtrar (opcional). Si no se indica, se consideran todos.",
}


@herramienta(
    descripcion=(
        "Busca símbolos disponibles en el broker (MT5) por nombre, descripción o categoría "
        "(ej. 'gold', 'euro', 'apple', 'US500'). Úsala para encontrar el nombre exacto de un activo."
    ),
    parametros={
        "texto": {"type": "string", "description": "Texto a buscar."},
        "max_resultados": {"type": "integer", "description": "Máximo de resultados (1-40). Por defecto 15."},
    },
    requeridos=["texto"],
    nombre="mt5_buscar_simbolos",
)
def mt5_buscar_simbolos(texto: str, max_resultados: int = 15) -> dict:
    return fuente.buscar_simbolos(texto, max_resultados)


@herramienta(
    descripcion=(
        "Cotización en tiempo real de un activo desde MT5: bid, ask, spread, máximo y mínimo del día, "
        "variación del día y hora del último tick."
    ),
    parametros={"simbolo": _SIMBOLO},
    requeridos=["simbolo"],
    nombre="mt5_precio",
)
def mt5_precio(simbolo: str) -> dict:
    return fuente.precio(simbolo)


@herramienta(
    descripcion=(
        "Velas (OHLC + volumen) de MT5. Devuelve resumen estadístico de las velas solicitadas "
        "y el detalle de las últimas N. Timeframes válidos: M1, M5, M15, M30, H1, H4, D1, W1, MN1."
    ),
    parametros={
        "simbolo": _SIMBOLO,
        "timeframe": {
            "type": "string",
            "enum": list(fuente.TIMEFRAMES),
            "description": "Temporalidad de cada vela. Por defecto H1.",
        },
        "cantidad": {"type": "integer", "description": "Cuántas velas recientes analizar (1-5000). Por defecto 100."},
        "ultimas_velas": {
            "type": "integer",
            "description": "Cuántas velas recientes devolver en detalle (0-200). Por defecto 20.",
        },
        "desde": {"type": "string", "description": "Fecha inicial AAAA-MM-DD (opcional)."},
        "hasta": {"type": "string", "description": "Fecha final AAAA-MM-DD (opcional)."},
    },
    requeridos=["simbolo"],
    nombre="mt5_velas",
)
def mt5_velas(
    simbolo: str,
    timeframe: str = "H1",
    cantidad: int = 100,
    ultimas_velas: int = 20,
    desde: str | None = None,
    hasta: str | None = None,
) -> dict:
    return fuente.velas(simbolo, timeframe, cantidad, ultimas_velas, desde, hasta)


@herramienta(
    descripcion=(
        "Estado de la cuenta del broker en MT5: tipo (demo o REAL), moneda, apalancamiento, balance, "
        "equity, beneficio flotante, margen usado y libre, y nivel de margen."
    ),
    nombre="mt5_cuenta",
)
def mt5_cuenta() -> dict:
    return fuente.cuenta()


@herramienta(
    descripcion=(
        "Posiciones abiertas ahora en la cuenta: símbolo, tipo, volumen, precio de apertura y actual, "
        "stop loss, take profit y beneficio flotante."
    ),
    parametros={"simbolo": _SIMBOLO_OPCIONAL},
    nombre="mt5_posiciones",
)
def mt5_posiciones(simbolo: str | None = None) -> dict:
    return fuente.posiciones(simbolo)


@herramienta(
    descripcion=(
        "Órdenes pendientes (límite, stop) de la cuenta que todavía no se han ejecutado."
    ),
    parametros={"simbolo": _SIMBOLO_OPCIONAL},
    nombre="mt5_ordenes_pendientes",
)
def mt5_ordenes_pendientes(simbolo: str | None = None) -> dict:
    return fuente.ordenes_pendientes(simbolo)


@herramienta(
    descripcion=(
        "Historial de operaciones CERRADAS de la cuenta en los últimos N días, con estadísticas."
    ),
    parametros={
        "dias": {"type": "integer", "description": "Cuántos días hacia atrás (1-365). Por defecto 30."},
        "simbolo": _SIMBOLO_OPCIONAL,
        "ultimas": {"type": "integer", "description": "Cuántas operaciones recientes detallar (0-100). Por defecto 15."},
    },
    nombre="mt5_historial_operaciones",
)
def mt5_historial_operaciones(dias: int = 30, simbolo: str | None = None, ultimas: int = 15) -> dict:
    return fuente.historial_operaciones(dias, simbolo, ultimas)