"""Herramientas registradas para el agente (los esquemas viven en esquemas.json)."""
from pathlib import Path

from fuentes import mt5_fuentes as fuente
from herramientas_agente.base import cargar_json, herramienta
from herramientas_agente.mt5_herramientas.auxiliares import _SIMBOLO

_ESQ = cargar_json(Path(__file__).parent / "esquemas.json")


@herramienta(**_ESQ["mt5_buscar_simbolos"])
def mt5_buscar_simbolos(texto: str, max_resultados: int = 15) -> dict:
    return fuente.buscar_simbolos(texto, max_resultados)


@herramienta(**_ESQ["mt5_precio"])
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


@herramienta(**_ESQ["mt5_cuenta"])
def mt5_cuenta() -> dict:
    return fuente.cuenta()


@herramienta(**_ESQ["mt5_posiciones"])
def mt5_posiciones(simbolo: str | None = None) -> dict:
    return fuente.posiciones(simbolo)


@herramienta(**_ESQ["mt5_ordenes_pendientes"])
def mt5_ordenes_pendientes(simbolo: str | None = None) -> dict:
    return fuente.ordenes_pendientes(simbolo)


@herramienta(**_ESQ["mt5_historial_operaciones"])
def mt5_historial_operaciones(dias: int = 30, simbolo: str | None = None, ultimas: int = 15) -> dict:
    return fuente.historial_operaciones(dias, simbolo, ultimas)
