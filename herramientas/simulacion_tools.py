"""Módulo de herramientas de simulación y análisis de escenarios 'What-If' para el agente.

NOMBRE DEL ARCHIVO: herramientas/simulacion_tools.py
"""

from __future__ import annotations

import json
from typing import Any

from fuentes import mt5_fuentes as mt5_fuente
from fuentes import investing_fuente as inv_fuente
from herramientas.base import herramienta


# ──────────────────────────────────────────────────────────────
# Matriz de Sensibilidad / Elasticidad Cruzada por Defecto
# ──────────────────────────────────────────────────────────────
# Muestra la elasticidad estimada (Beta cruzado) entre activos cuando no hay posición directa.
ELASTICIDAD_CRUZADA: dict[str, dict[str, float]] = {
    "USDCLP": {
        "EURUSD": -0.30,  # Un alza de 1% en USD/CLP suele coincidir con -0.30% en EUR/USD (fortaleza del USD)
        "GBPUSD": -0.25,
        "XAUUSD": -0.20,
    },
    "EURUSD": {
        "GBPUSD": 0.80,   # Alta correlación positiva
        "USDCHF": -0.85,  # Correlación inversa fuerte
        "USDCLP": -0.40,
    },
    "CL=F": {             # Petróleo WTI
        "USDCAD": -0.55,  # Dólar canadiense se fortalece con el petróleo
    },
    "GC=F": {             # Oro
        "XAUUSD": 1.00,
        "USDJPY": -0.35,
    },
}


def _normalizar_simbolo(simbolo: str) -> str:
    s = (simbolo or "").strip().upper().replace("/", "").replace("-", "")
    if s in ("GOLD", "XAUUSD"):
        return "XAUUSD"
    if s in ("OIL", "WTI", "CL"):
        return "CL=F"
    return s


def _estimar_tamano_contrato(simbolo: str) -> float:
    s = _normalizar_simbolo(simbolo)
    if "XAU" in s or "GOLD" in s:
        return 100.0  # 100 oz por lote
    if "CL" in s or "OIL" in s:
        return 1000.0  # 1000 barriles
    if "US500" in s or "SPX" in s or "NAS100" in s:
        return 10.0
    return 100000.0  # Forex estándar: 100.000 unidades


# ──────────────────────────────────────────────────────────────
# Herramienta del Agente
# ──────────────────────────────────────────────────────────────

@herramienta(
    descripcion=(
        "Simula el impacto monetario y de margen en toda la cartera ante un escenario 'What-If' "
        "(ej: '¿Qué pasa si el USD/CLP sube 3%?' o '¿Qué ocurre si el EUR/USD cae 1.5%?'). "
        "Calcula el impacto directo, indirecto por correlación, la equidad proyectada, "
        "el nivel de margen resultante y detecta alertas de Margin Call o Stop Out."
    ),
    parametros={
        "variaciones_pct": {
            "type": "string",
            "description": (
                "Diccionario en texto o JSON con los activos a simular y sus variaciones porcentuales. "
                "Ejemplos: '{\"USDCLP\": 3.0}' o '{\"EURUSD\": -1.5, \"USDCLP\": 2.0}'."
            ),
        },
        "incluir_noticias_contexto": {
            "type": "boolean",
            "description": "Si es True, consulta Investing.com para traer contexto macroeconómico reciente. Por defecto True.",
        },
    },
    requeridos=["variaciones_pct"],
    nombre="simular_escenario_cartera",
)
def simular_escenario_cartera(
    variaciones_pct: str | dict[str, float],
    incluir_noticias_contexto: bool = True,
) -> dict[str, Any]:
    # Parsear parámetro de entrada
    if isinstance(variaciones_pct, str):
        try:
            variaciones_dict: dict[str, float] = json.loads(variaciones_pct)
        except Exception:
            # Fallback para cadenas simples tipo "USDCLP:3.0"
            variaciones_dict = {}
            for par in variaciones_pct.replace("{", "").replace("}", "").split(","):
                if ":" in par:
                    k, v = par.split(":", 1)
                    variaciones_dict[k.strip().replace('"', '')] = float(v.strip())
    else:
        variaciones_dict = variaciones_pct

    variaciones_norm = {_normalizar_simbolo(k): float(v) for k, v in variaciones_dict.items()}

    # Obtener estado actual de la cuenta y posiciones
    cuenta = mt5_fuente.cuenta()
    posiciones_data = mt5_fuente.posiciones()

    equidad_actual = cuenta.get("equidad") or 0.0
    balance_actual = cuenta.get("balance") or 0.0
    margen_usado = cuenta.get("margen_usado") or 0.0
    nivel_margen_actual = cuenta.get("nivel_margen") or 0.0
    pnl_flotante_actual = cuenta.get("beneficio_flotante") or 0.0

    posiciones = posiciones_data.get("posiciones", [])

    desglose_posiciones = []
    pnl_simulado_total = 0.0

    for pos in posiciones:
        ticket = pos["ticket"]
        sym_raw = pos["simbolo"]
        sym_norm = _normalizar_simbolo(sym_raw)
        tipo = pos["tipo"]  # "COMPRA" o "VENTA"
        lotes = pos["lotes"]
        precio_act = pos["precio_actual"]
        pnl_actual = pos["beneficio"]

        # Determinar la variación porcentual proyectada para este activo
        var_pct_aplicada = 0.0
        tipo_impacto = "NINGUNO"

        if sym_norm in variaciones_norm:
            # Impacto directo
            var_pct_aplicada = variaciones_norm[sym_norm]
            tipo_impacto = "DIRECTO"
        else:
            # Impacto indirecto vía sensibilidad / correlación
            for causa, var_causa in variaciones_norm.items():
                if causa in ELASTICIDAD_CRUZADA and sym_norm in ELASTICIDAD_CRUZADA[causa]:
                    beta = ELASTICIDAD_CRUZADA[causa][sym_norm]
                    var_pct_aplicada = var_causa * beta
                    tipo_impacto = f"INDIRECTO (vía {causa}, Beta={beta})"
                    break

        # Cálculo del cambio de PnL
        contract_size = _estimar_tamano_contrato(sym_raw)
        valor_nocional = precio_act * lotes * contract_size
        
        # En COMPRA: subida (+%) es ganancia. En VENTA: subida (+%) es pérdida.
        multiplicador_tipo = 1.0 if tipo == "COMPRA" else -1.0
        delta_pnl = valor_nocional * (var_pct_aplicada / 100.0) * multiplicador_tipo
        pnl_proyectado = pnl_actual + delta_pnl
        pnl_simulado_total += delta_pnl

        desglose_posiciones.append({
            "ticket": ticket,
            "simbolo": sym_raw,
            "tipo": tipo,
            "lotes": lotes,
            "precio_actual": precio_act,
            "variacion_simulada_pct": round(var_pct_aplicada, 2),
            "tipo_impacto": tipo_impacto,
            "pnl_flotante_actual_usd": round(pnl_actual, 2),
            "impacto_estimado_usd": round(delta_pnl, 2),
            "pnl_flotante_proyectado_usd": round(pnl_proyectado, 2),
        })

    # Recálculo de métricas de cuenta
    equidad_proyectada = equidad_actual + pnl_simulado_total
    pnl_flotante_proyectado_total = pnl_flotante_actual + pnl_simulado_total
    
    nivel_margen_proyectado = (
        round((equidad_proyectada / margen_usado) * 100.0, 2)
        if margen_usado > 0
        else 999.0
    )

    variacion_equidad_pct = (
        round(((equidad_proyectada - equidad_actual) / equidad_actual) * 100.0, 2)
        if equidad_actual > 0
        else 0.0
    )

    # Evaluación de estado de riesgo
    if nivel_margen_proyectado <= 50.0:
        estado_riesgo = "CRÍTICO - STOP OUT (Riesgo inminente de liquidación forzosa)"
    elif nivel_margen_proyectado <= 100.0:
        estado_riesgo = "ALERTA - MARGIN CALL (Insuficiencia de margen libre)"
    elif variacion_equidad_pct <= -15.0:
        estado_riesgo = "ADVERTENCIA - DRAWDOWN ELEVADO (>15% de la equidad)"
    elif variacion_equidad_pct < 0:
        estado_riesgo = "MODERADO - Impacto negativo controlado"
    else:
        estado_riesgo = "POSITIVO - Impacto favorable en cartera"

    # Noticias macro de contexto (vía Investing.com)
    noticias_contexto = []
    if incluir_noticias_contexto:
        for causa in variaciones_norm.keys():
            try:
                # Búsqueda de noticias relacionadas
                res_noticias = inv_fuente.buscar_noticias(busqueda=causa, categoria="forex", cantidad=3)
                noticias_contexto.extend(res_noticias.get("noticias", []))
            except Exception:
                pass

    return {
        "fuente": "Motor de Simulación Mt5 + Investing.com",
        "escenario_simulado": variaciones_norm,
        "resumen_cartera": {
            "equidad_actual_usd": round(equidad_actual, 2),
            "equidad_proyectada_usd": round(equidad_proyectada, 2),
            "variacion_equidad_usd": round(pnl_simulado_total, 2),
            "variacion_equidad_pct": variacion_equidad_pct,
            "nivel_margen_actual_pct": round(nivel_margen_actual, 2),
            "nivel_margen_proyectado_pct": nivel_margen_proyectado,
            "estado_riesgo_cartera": estado_riesgo,
        },
        "impacto_por_posicion": desglose_posiciones,
        "contexto_noticias_macro": noticias_contexto[:5],
    }