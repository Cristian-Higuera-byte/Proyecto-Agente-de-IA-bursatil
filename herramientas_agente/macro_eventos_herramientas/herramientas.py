"""Herramientas registradas para el agente (los esquemas viven en esquemas.json)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fuentes import investing_fuente
from herramientas_agente.base import cargar_json, herramienta
from herramientas_agente.macro_eventos_herramientas.auxiliares import CATEGORIAS, _DIVISAS, _EVENTOS

_ESQ = cargar_json(Path(__file__).parent / "esquemas.json")


@herramienta(**_ESQ["evaluar_riesgo_noticias_proximas"])
def evaluar_riesgo_noticias_proximas(
    divisa: str = "ALL",
    cantidad_titulares: int = 20,
) -> dict[str, Any]:
    divisa_clean = (divisa or "ALL").strip().upper()
    claves_divisa = _DIVISAS.get(divisa_clean)

    titulares: list[dict[str, Any]] = []
    fallos = 0
    for categoria in CATEGORIAS:
        try:
            res = investing_fuente.noticias(categoria=categoria, cantidad=cantidad_titulares)
        except Exception:  # noqa: BLE001 - se informa abajo; no se inventa nada
            fallos += 1
            continue
        titulares.extend(res.get("noticias", []))

    if fallos == len(CATEGORIAS):
        return {
            "fuente": "Investing.com (titulares)",
            "disponible": False,
            "mensaje": (
                "No se pudieron obtener noticias de Investing.com, así que no se puede evaluar el riesgo "
                "macro. No hay datos de calendario económico."
            ),
        }

    vistos: set[str] = set()
    relevantes: list[dict[str, Any]] = []
    for n in titulares:
        titulo = n.get("titulo", "")
        if not titulo or titulo in vistos:
            continue
        vistos.add(titulo)
        texto = f"{titulo} {n.get('resumen') or ''}".lower()
        if not any(p in texto for p in _EVENTOS):
            continue
        if claves_divisa and not any(p in texto for p in claves_divisa):
            continue
        relevantes.append({k: n.get(k) for k in ("titulo", "fecha", "enlace")})

    if relevantes:
        nivel = "PRECAUCIÓN"
        lectura = (
            f"{len(relevantes)} titular(es) reciente(s) hablan de eventos macro de alto impacto. Conviene "
            "revisar la hora exacta del evento en un calendario económico antes de abrir operaciones o ajustar stops."
        )
    else:
        nivel = "SIN SEÑALES EN TITULARES"
        lectura = (
            "No se detectaron titulares sobre eventos de alto impacto, pero esto NO garantiza que no haya "
            "eventos próximos: no hay un calendario económico conectado."
        )

    return {
        "fuente": "Investing.com (titulares recientes; no es un calendario económico)",
        "disponible": True,
        "divisa_evaluada": divisa_clean,
        "titulares_revisados": len(vistos),
        "nivel_cautela_macro": nivel,
        "titulares_alto_impacto": relevantes[:8],
        "lectura": lectura,
        "limitacion": "Sin horas exactas ni cifras previstas/anteriores de los eventos.",
    }
