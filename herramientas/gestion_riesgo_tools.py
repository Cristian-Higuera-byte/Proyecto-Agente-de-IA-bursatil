"""Módulo de gestión de riesgo, optimización de lote y exposición por divisa.

NOMBRE DEL ARCHIVO: herramientas/gestion_riesgo_tools.py
"""

from __future__ import annotations

from typing import Any

from fuentes import mt5_fuentes as mt5_fuente
from herramientas.base import herramienta


@herramienta(
    descripcion=(
        "Calcula el tamaño exacto de la posición (lotaje) basado en el porcentaje de riesgo del capital, "
        "la distancia del Stop Loss en pips/puntos y el valor estimado del pip."
    ),
    parametros={
        "simbolo": {
            "type": "string",
            "description": "Símbolo del activo (ej. 'EURUSD', 'USDCLP', 'XAUUSD').",
        },
        "distancia_sl_pips": {
            "type": "number",
            "description": "Distancia del Stop Loss en pips o puntos.",
        },
        "porcentaje_riesgo": {
            "type": "number",
            "description": "Porcentaje máximo de capital a arriesgar (ej. 1.0 para 1%). Por defecto 1.0.",
        },
        "capital_usd": {
            "type": "number",
            "description": "Capital base en USD. Si no se especifica, toma la equidad actual de MT5.",
        },
    },
    requeridos=["simbolo", "distancia_sl_pips"],
    nombre="calcular_tamano_posicion",
)
def calcular_tamano_posicion(
    simbolo: str,
    distancia_sl_pips: float,
    porcentaje_riesgo: float = 1.0,
    capital_usd: float | None = None,
) -> dict[str, Any]:
    if distancia_sl_pips <= 0:
        return {"error": "La distancia del Stop Loss debe ser mayor a 0."}

    cuenta = mt5_fuente.cuenta()
    capital = capital_usd or cuenta.get("equidad") or 10000.0
    monto_riesgo_usd = capital * (porcentaje_riesgo / 100.0)

    sym_upper = simbolo.strip().upper()

    # Estimación de valor por pip en USD por 1.0 lote estándar (100,000 unidades)
    if "USD" in sym_upper and sym_upper.endswith("USD"):
        valor_pip_lote_estandar = 10.0  # ej. EURUSD, GBPUSD, AUDUSD
    elif sym_upper.startswith("USD"):
        valor_pip_lote_estandar = 8.5   # ej. USDJPY, USDCAD, USDCHF
    elif sym_upper in ("XAUUSD", "GOLD"):
        valor_pip_lote_estandar = 10.0  # 1 pip = $0.10 en oro
    else:
        valor_pip_lote_estandar = 10.0  # Valor base general

    lote_calculado = monto_riesgo_usd / (distancia_sl_pips * valor_pip_lote_estandar)
    lote_sugerido = max(0.01, round(lote_calculado, 2))

    return {
        "fuente": "Calculadora de Gestión de Riesgo y Lote",
        "simbolo": sym_upper,
        "capital_evaluado_usd": capital,
        "porcentaje_riesgo_pct": porcentaje_riesgo,
        "monto_arriesgado_usd": round(monto_riesgo_usd, 2),
        "distancia_sl_pips": distancia_sl_pips,
        "lotaje_teorico": round(lote_calculado, 4),
        "lotaje_sugerido": lote_sugerido,
        "valor_pip_estimado_por_lote_usd": valor_pip_lote_estandar,
    }


@herramienta(
    descripcion=(
        "Calcula la fracción óptima de capital a arriesgar utilizando la Fórmula de Criterio de Kelly "
        "y Criterio de Half-Kelly (conservador) según la tasa de acierto y el ratio Riesgo/Beneficio."
    ),
    parametros={
        "win_rate_pct": {
            "type": "number",
            "description": "Tasa de acierto en porcentaje (ej. 55 para 55%).",
        },
        "ratio_rr": {
            "type": "number",
            "description": "Ratio Riesgo/Beneficio medio (ej. 1.5 si ganas $1.5 por cada $1 arriesgado).",
        },
    },
    requeridos=["win_rate_pct", "ratio_rr"],
    nombre="calcular_criterio_kelly",
)
def calcular_criterio_kelly(
    win_rate_pct: float,
    ratio_rr: float,
) -> dict[str, Any]:
    if ratio_rr <= 0 or win_rate_pct < 0 or win_rate_pct > 100:
        return {"error": "Parámetros inválidos. Win rate debe estar entre 0 y 100, y RR debe ser mayor a 0."}

    p = win_rate_pct / 100.0  # Probabilidad de ganar
    q = 1.0 - p               # Probabilidad de perder
    b = ratio_rr              # Ratio Beneficio/Riesgo

    # Fórmula de Kelly: K% = (b * p - q) / b
    kelly_fraction = (b * p - q) / b if b > 0 else 0.0
    kelly_pct = max(0.0, kelly_fraction * 100.0)

    half_kelly_pct = kelly_pct / 2.0
    quarter_kelly_pct = kelly_pct / 4.0

    expectativa_matematica = (p * b) - q

    return {
        "fuente": "Optimizador de Criterio de Kelly",
        "parametros_entrada": {
            "win_rate_pct": win_rate_pct,
            "ratio_riesgo_beneficio": ratio_rr,
        },
        "expectativa_matematica_esperada_por_unidad": round(expectativa_matematica, 4),
        "resultados_kelly": {
            "full_kelly_pct": round(kelly_pct, 2),
            "half_kelly_sugerido_pct": round(half_kelly_pct, 2),
            "quarter_kelly_conservador_pct": round(quarter_kelly_pct, 2),
        },
        "diagnostico": (
            "Expectativa matemática positiva. Se recomienda aplicar Half-Kelly para mitigar volatilidad."
            if expectativa_matematica > 0
            else "Expectativa matemática negativa o nula. No se recomienda ejecutar esta estrategia."
        ),
    }


@herramienta(
    descripcion=(
        "Analiza la exposición neta consolidada por divisa/moneda individual "
        "a través de todas las posiciones abiertas en la cuenta de MT5."
    ),
    parametros={},
    nombre="analizar_exposicion_divisas",
)
def analizar_exposicion_divisas() -> dict[str, Any]:
    posiciones = mt5_fuente.posiciones().get("posiciones", [])
    if not posiciones:
        return {
            "fuente": "Desglose de Exposición por Divisa",
            "total_posiciones": 0,
            "exposicion_por_divisa": {},
            "mensaje": "No hay posiciones abiertas activas en la cuenta.",
        }

    exposicion: dict[str, dict[str, float]] = {}

    for pos in posiciones:
        sym = pos.get("simbolo", "").upper()
        volumen = pos.get("volumen", 0.0)
        tipo = pos.get("tipo", "BUY").upper()

        if len(sym) == 6 and sym.isalpha():
            base = sym[:3]
            quote = sym[3:]
        elif "USD" in sym and sym != "USD":
            base = sym.replace("USD", "")
            quote = "USD"
        else:
            base = sym
            quote = "USD"

        if base not in exposicion:
            exposicion[base] = {"volumen_comprado": 0.0, "volumen_vendido": 0.0, "exposicion_neta": 0.0}
        if quote not in exposicion:
            exposicion[quote] = {"volumen_comprado": 0.0, "volumen_vendido": 0.0, "exposicion_neta": 0.0}

        if tipo in ("BUY", "COMPRA"):
            exposicion[base]["volumen_comprado"] += volumen
            exposicion[quote]["volumen_vendido"] += volumen
        else:
            exposicion[base]["volumen_vendido"] += volumen
            exposicion[quote]["volumen_comprado"] += volumen

    for div, datos in exposicion.items():
        datos["volumen_comprado"] = round(datos["volumen_comprado"], 2)
        datos["volumen_vendido"] = round(datos["volumen_vendido"], 2)
        datos["exposicion_neta"] = round(datos["volumen_comprado"] - datos["volumen_vendido"], 2)

    return {
        "fuente": "Desglose de Exposición por Divisa",
        "total_posiciones_analizadas": len(posiciones),
        "exposicion_por_divisa": exposicion,
    }