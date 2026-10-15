"""Noticias de un símbolo y consenso de analistas."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import yfinance as yf  # type: ignore[import-untyped]

from fuentes.yfinance_fuente.cache import _cacheado
from fuentes.yfinance_fuente.utiles import _entero, _fmt_fecha, _num, _simbolo, _sin_nulos


# ──────────────────────────────────────────────────────────────
# Noticias
# ──────────────────────────────────────────────────────────────
def _normalizar_noticia(item: dict[str, Any] | None) -> dict[str, Any] | None:
    """Yahoo ha cambiado el formato de las noticias; aquí se soportan el nuevo y el antiguo."""
    if not isinstance(item, dict):
        return None

    c = item.get("content") if isinstance(item.get("content"), dict) else item
    if not isinstance(c, dict):
        return None

    titulo = c.get("title")
    if not titulo:
        return None

    proveedor = c.get("provider")
    fuente = proveedor.get("displayName") if isinstance(proveedor, dict) else c.get("publisher")

    fecha = c.get("pubDate") or c.get("displayTime")
    provider_publish_time = c.get("providerPublishTime")
    if not fecha and isinstance(provider_publish_time, (int, float)):
        fecha = datetime.fromtimestamp(provider_publish_time, tz=timezone.utc).isoformat(timespec="seconds")

    url = None
    for clave in ("canonicalUrl", "clickThroughUrl"):
        v = c.get(clave)
        if isinstance(v, dict) and v.get("url"):
            url = v["url"]
            break
    url = url or c.get("link")

    resumen = c.get("summary") or c.get("description")
    if isinstance(resumen, str) and len(resumen) > 300:
        resumen = resumen[:300] + "..."

    return _sin_nulos({"titulo": titulo, "resumen": resumen, "fuente": fuente, "fecha": fecha, "url": url})


def noticias(simbolo: str, cantidad: int = 8) -> list[dict[str, Any]]:
    s = _simbolo(simbolo)
    n = max(1, min(int(cantidad), 20))

    def _fn() -> list[dict[str, Any]]:
        ticker = yf.Ticker(s)
        try:
            crudo = ticker.get_news(count=n)
        except (AttributeError, TypeError):  # versiones antiguas de yfinance
            crudo = ticker.news
        normalizadas = (_normalizar_noticia(i) for i in (crudo or []))
        return [x for x in normalizadas if x][:n]

    return _cacheado(f"noticias:{s}:{n}", 300, _fn)


# ──────────────────────────────────────────────────────────────
# Consenso de analistas
# ──────────────────────────────────────────────────────────────
def consenso_analistas(simbolo: str) -> dict[str, Any]:
    s = _simbolo(simbolo)

    def _fn() -> dict[str, Any]:
        ticker = yf.Ticker(s)
        resultado: dict[str, Any] = {"simbolo": s}

        try:
            objetivos = ticker.analyst_price_targets
            if objetivos:
                resultado["precio_objetivo"] = {k: _num(v) for k, v in objetivos.items()}
        except Exception:  # noqa: BLE001
            pass

        try:
            df = ticker.recommendations_summary
            if df is not None and not df.empty:
                resultado["recomendaciones"] = [
                    {k: (v if isinstance(v, str) else _entero(v)) for k, v in fila.items()}
                    for fila in df.head(2).to_dict("records")
                ]
        except Exception:  # noqa: BLE001
            pass

        if len(resultado) == 1:
            raise ValueError(f"Sin datos de analistas para '{s}' (solo existen para acciones y algunos ETF).")
        resultado["nota"] = "recomendaciones: conteo de analistas por periodo ('0m' = mes actual, '-1m' = mes anterior)."
        return resultado

    return _cacheado(f"analistas:{s}", 3600, _fn)
