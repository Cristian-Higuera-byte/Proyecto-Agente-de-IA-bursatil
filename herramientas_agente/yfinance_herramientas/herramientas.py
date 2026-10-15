"""Herramientas registradas para el agente (los esquemas viven en esquemas.json)."""
from pathlib import Path

from fuentes import yfinance_fuente as fuente
from herramientas_agente.base import cargar_json, herramienta
from herramientas_agente.yfinance_herramientas.auxiliares import _SIMBOLO

_ESQ = cargar_json(Path(__file__).parent / "esquemas.json")


@herramienta(**_ESQ["yf_buscar_simbolo"])
def yf_buscar_simbolo(consulta: str, max_resultados: int = 8) -> list:
    return fuente.buscar(consulta, max_resultados)


@herramienta(**_ESQ["yf_cotizacion"])
def yf_cotizacion(simbolo: str) -> dict:
    return fuente.cotizacion(simbolo)


@herramienta(
    descripcion=(
        "Histórico de precios (OHLCV) de Yahoo Finance. Devuelve un resumen estadístico de TODO "
        "el rango (variación %, máximo, mínimo, volatilidad) más las últimas N velas. "
        "Usa 'periodo' o bien 'inicio'/'fin' (si das 'inicio', se ignora 'periodo'). "
        "Los intervalos intradía solo tienen datos recientes (1m: 7 días; el resto: ~60 días)."
    ),
    parametros={
        "simbolo": _SIMBOLO,
        "periodo": {
            "type": "string",
            "enum": list(fuente.PERIODOS),
            "description": "Rango hacia atrás desde hoy. Por defecto 3mo.",
        },
        "intervalo": {
            "type": "string",
            "enum": list(fuente.INTERVALOS),
            "description": "Tamaño de cada vela. Por defecto 1d.",
        },
        "inicio": {"type": "string", "description": "Fecha inicial AAAA-MM-DD (opcional)."},
        "fin": {"type": "string", "description": "Fecha final AAAA-MM-DD (opcional; por defecto hoy)."},
        "ultimas_velas": {
            "type": "integer",
            "description": "Cuántas velas recientes incluir en detalle (0-200). Por defecto 20.",
        },
    },
    requeridos=["simbolo"],
    nombre="yf_historico",
)
def yf_historico(
    simbolo: str,
    periodo: str = "3mo",
    intervalo: str = "1d",
    inicio: str | None = None,
    fin: str | None = None,
    ultimas_velas: int = 20,
) -> dict:
    return fuente.historico(simbolo, periodo, intervalo, inicio, fin, ultimas_velas)


@herramienta(**_ESQ["yf_fundamentales"])
def yf_fundamentales(simbolo: str) -> dict:
    return fuente.fundamentales(simbolo)


@herramienta(**_ESQ["yf_estados_financieros"])
def yf_estados_financieros(
    simbolo: str, tipo: str = "resultados", frecuencia: str = "anual", periodos: int = 4
) -> dict:
    return fuente.estados_financieros(simbolo, tipo, frecuencia, periodos)


@herramienta(**_ESQ["yf_noticias"])
def yf_noticias(simbolo: str, cantidad: int = 8) -> list:
    return fuente.noticias(simbolo, cantidad)


@herramienta(**_ESQ["yf_consenso_analistas"])
def yf_consenso_analistas(simbolo: str) -> dict:
    return fuente.consenso_analistas(simbolo)
