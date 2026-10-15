"""Herramientas registradas para el agente (los esquemas viven en esquemas.json)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fuentes import mt5_fuentes as mt5_fuente
from herramientas_agente import analisis_herramientas
from herramientas_agente.base import cargar_json, herramienta
from herramientas_agente.informe_cartera_herramientas.auxiliares import (
    _alertas,
    _correlaciones,
    _escenarios,
    _exposicion,
    _noticias,
    _volatilidad,
)

_ESQ = cargar_json(Path(__file__).parent / "esquemas.json")


@herramienta(**_ESQ["informe_cartera"])
def informe_cartera() -> dict[str, Any]:
    cuenta = mt5_fuente.cuenta()
    posiciones = mt5_fuente.posiciones().get("posiciones", [])
    equidad = cuenta.get("equidad") or 0.0
    if not posiciones:
        return {
            "fuente": "MetaTrader 5",
            "total_posiciones": 0,
            "cuenta": cuenta,
            "mensaje": "No hay posiciones abiertas: no hay exposición ni riesgo en la cartera.",
        }

    fallos: dict[str, str] = {}

    def seccion(nombre: str, fn: Any, defecto: Any) -> Any:
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 - una sección caída no invalida las demás
            fallos[nombre] = str(e)[:160]
            return defecto

    riesgo = seccion("riesgo", analisis_herramientas.analizar_riesgo_posicion, {})
    expo = seccion("exposicion", lambda: _exposicion(posiciones, equidad), {})
    vol = seccion("volatilidad", lambda: _volatilidad(sorted({p["simbolo"] for p in posiciones})), {})
    corr = seccion("correlaciones", lambda: _correlaciones(posiciones), {})
    noticias = seccion("noticias", lambda: _noticias(posiciones), {})
    esc = seccion("escenarios", lambda: _escenarios(posiciones, vol, riesgo, equidad), {})
    alertas = seccion("alertas", lambda: _alertas(cuenta, riesgo, expo, corr, noticias), [])
    expo.pop("_mayor_divisa", None)

    return {
        "fuente": "MetaTrader 5 + Investing.com (titulares)",
        "total_posiciones": len(posiciones),
        "cuenta": {k: cuenta.get(k) for k in ("tipo", "moneda", "balance", "equidad", "beneficio_flotante",
                                              "margen_usado", "margen_libre", "nivel_margen_pct")},
        "alertas": alertas,
        "exposicion": expo,
        "riesgo": {k: riesgo.get(k) for k in ("riesgo_total_acumulado_usd", "riesgo_total_equidad_pct",
                                              "posiciones_sin_stop_loss", "aviso", "posiciones")},
        "volatilidad": vol,
        "correlaciones": corr,
        "noticias": noticias,
        "escenarios": esc,
        "secciones_no_disponibles": fallos,
    }
