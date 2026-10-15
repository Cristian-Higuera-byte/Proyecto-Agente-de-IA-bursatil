"""Extracción de noticias del RSS de Investing.com y búsqueda por palabra clave."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

import requests

from fuentes.investing_fuente.cache import _cacheado
from fuentes.investing_fuente.constantes import AVISO_FUENTE, FEEDS, HEADERS
from fuentes.investing_fuente.errores import ErrorInvesting
from fuentes.investing_fuente.utiles import _limpiar_html, _sin_nulos


# ──────────────────────────────────────────────────────────────
# Extracción de Noticias
# ──────────────────────────────────────────────────────────────
def noticias(categoria: str = "general", cantidad: int = 10) -> dict[str, Any]:
    """Obtiene las últimas noticias publicadas en Investing.com para una categoría dada.

    Categorías válidas: 'general', 'mercados', 'forex', 'acciones', 'cripto', 'economia'.
    """
    cat = (categoria or "general").strip().lower()
    if cat not in FEEDS:
        raise ErrorInvesting(
            f"Categoría inválida: {categoria!r}. Opciones permitidas: {', '.join(FEEDS.keys())}"
        )

    n = max(1, min(int(cantidad), 30))
    url = FEEDS[cat]

    def _fn() -> dict[str, Any]:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise ErrorInvesting(
                f"No se pudo conectar con Investing.com ({cat}): {e}"
            ) from e

        try:
            root = ET.fromstring(resp.content)
            channel = root.find("channel")
            if channel is None:
                raise ErrorInvesting("El feed RSS de Investing.com no devolvió un canal válido.")
        except ET.ParseError as e:
            raise ErrorInvesting(
                f"Error al procesar la respuesta XML de Investing.com: {e}"
            ) from e

        items = channel.findall("item")
        resultado = []

        for item in items[:n]:
            titulo = item.findtext("title", default="").strip()
            enlace = item.findtext("link", default="").strip()
            fecha_raw = item.findtext("pubDate", default="").strip()
            descripcion_raw = item.findtext("description", default="")

            resumen = _limpiar_html(descripcion_raw)
            if len(resumen) > 300:
                resumen = resumen[:300] + "..."

            if titulo:
                resultado.append(
                    _sin_nulos(
                        {
                            "titulo": titulo,
                            "resumen": resumen or None,
                            "fecha": fecha_raw or None,
                            "enlace": enlace or None,
                        }
                    )
                )

        return {
            "fuente": "Investing.com",
            "categoria": cat,
            "noticias_totales": len(resultado),
            "noticias": resultado,
            "consultado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "aviso": AVISO_FUENTE,
        }

    # Cache de 5 minutos (300 segundos) para noticias
    return _cacheado(f"investing:{cat}:{n}", 300, _fn)


def buscar_noticias(
    busqueda: str, categoria: str = "general", cantidad: int = 10
) -> dict[str, Any]:
    """Filtra las noticias recientes de una categoría por una palabra clave (ej. 'FED', 'Oro', 'Inflación')."""
    palabra = (busqueda or "").strip().lower()
    if not palabra:
        raise ErrorInvesting("Falta el término de búsqueda.")

    datos_cat = noticias(categoria=categoria, cantidad=30)
    filtradas = [
        n for n in datos_cat["noticias"]
        if palabra in n["titulo"].lower() or palabra in (n.get("resumen") or "").lower()
    ]

    return {
        "fuente": "Investing.com",
        "busqueda": palabra,
        "categoria": categoria,
        "coincidencias": len(filtradas),
        "noticias": filtradas[:cantidad],
        "consultado_utc": datos_cat["consultado_utc"],
        "aviso": AVISO_FUENTE,
    }
