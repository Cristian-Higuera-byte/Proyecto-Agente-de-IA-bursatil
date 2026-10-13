"""Módulo de riesgo macroeconómico por noticias.

NOMBRE DEL ARCHIVO: herramientas/macro_eventos_tools.py

No hay una fuente de calendario económico con horas exactas conectada. Esta herramienta NO inventa
eventos: revisa los titulares reales y recientes de Investing.com y señala los que hablan de eventos
de alto impacto (nóminas, inflación, bancos centrales, PIB...). Es una señal por titulares, no un
calendario: no sirve para saber a qué hora sale un dato.
"""

from __future__ import annotations

from typing import Any

from fuentes import investing_fuente
from herramientas.base import herramienta

CATEGORIAS = ("economia", "forex", "mercados")

# Palabras (minúsculas) que delatan un evento macro de alto impacto en un titular.
_EVENTOS = (
    "nóminas", "nominas", "nfp", "empleo", "desempleo", "inflación", "inflacion", "ipc", "cpi", "pce",
    "pib", "gdp", "fomc", "reserva federal", "la fed", "powell", "bce", "lagarde", "banco de inglaterra",
    "banco de japón", "banco de japon", "tipos de interés", "tasas de interés", "tasas de interes",
    "decisión de tipos", "decision de tipos", "ventas minoristas", "pmi", "opep", "opec",
)

# Palabras que vinculan un titular con una divisa.
_DIVISAS = {
    "USD": ("dólar", "dolar", "ee.uu.", "estados unidos", "fed", "reserva federal", "powell", "usd"),
    "EUR": ("euro", "eurozona", "bce", "lagarde", "alemania", "eur"),
    "GBP": ("libra", "reino unido", "banco de inglaterra", "gbp"),
    "JPY": ("yen", "japón", "japon", "banco de japón", "jpy"),
    "CAD": ("canadá", "canada", "dólar canadiense", "cad"),
    "AUD": ("australia", "aud"),
    "CHF": ("franco suizo", "suiza", "chf"),
    "CLP": ("chile", "peso chileno", "clp", "cobre"),
    "XAU": ("oro", "xau", "gold"),
}


@herramienta(
    descripcion=(
        "Detecta, en los titulares recientes de Investing.com, noticias sobre eventos macroeconómicos de "
        "alto impacto (empleo, inflación, bancos centrales, PIB...) para una divisa o para todo el mercado, "
        "y da una señal de cautela. NO es un calendario económico: no entrega horas ni cifras previstas."
    ),
    parametros={
        "divisa": {
            "type": "string",
            "description": "Divisa a filtrar (ej. 'USD', 'EUR', 'GBP', 'JPY', 'XAU') o 'ALL'. Por defecto 'ALL'.",
        },
        "cantidad_titulares": {
            "type": "integer",
            "description": "Titulares a revisar por categoría (máximo 30). Por defecto 20.",
        },
    },
    nombre="evaluar_riesgo_noticias_proximas",
)
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
