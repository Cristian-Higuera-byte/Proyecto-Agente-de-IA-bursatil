"""Herramientas registradas para el agente (los esquemas viven en esquemas.json)."""
from pathlib import Path

from fuentes import investing_fuente as fuente
from herramientas_agente.base import cargar_json, herramienta

_ESQ = cargar_json(Path(__file__).parent / "esquemas.json")


@herramienta(**_ESQ["inv_noticias"])
def inv_noticias(categoria: str = "general", cantidad: int = 10) -> dict:
    return fuente.noticias(categoria=categoria, cantidad=cantidad)


@herramienta(**_ESQ["inv_buscar_noticias"])
def inv_buscar_noticias(
    busqueda: str, categoria: str = "general", cantidad: int = 10
) -> dict:
    return fuente.buscar_noticias(
        busqueda=busqueda, categoria=categoria, cantidad=cantidad
    )
