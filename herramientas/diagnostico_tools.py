"""Módulo de diagnóstico holístico de posiciones y activos para el agente.

NOMBRE DEL ARCHIVO: herramientas/diagnostico_tools.py
"""

from __future__ import annotations

from typing import Any

from fuentes import mt5_fuentes as mt5_fuente
from fuentes import yfinance_fuente as yf_fuente
from fuentes import investing_fuente as inv_fuente
from herramientas import analisis_tools
from herramientas.base import herramienta


def _mapear_simbolo_yfinance(simbolo: str) -> str:
    s = (simbolo or "").strip().upper().replace("/", "")
    if s == "EURUSD":
        return "EURUSD=X"
    if s == "USDCLP":
        return "USDCLP=X"
    if s == "GBPUSD":
        return "GBPUSD=X"
    if s in ("XAUUSD", "GOLD"):
        return "GC=F"
    if s in ("WTI", "CL"):
        return "CL=F"
    if s == "BTCUSD":
        return "BTC-USD"
    if not s.endswith("=X") and len(s) == 6 and s.isalpha():
        return f"{s}=X"
    return s


@herramienta(
    descripcion=(
        "Realiza un diagnóstico integral (holístico) de una posición abierta o un activo en MT5. "
        "Consolida exposición actual, análisis de riesgo (distancia a SL/TP, % equidad), "
        "volatilidad (ATR), indicadores técnicos (RSI, MACD, Medias Móviles), contexto de noticias "
        "macroeconómicas de Investing.com/Yahoo Finance y una matriz de 3 escenarios (Alcista, Neutral, Bajista)."
    ),
    parametros={
        "simbolo": {
            "type": "string",
            "description": "Símbolo del activo a diagnosticar (ej. 'EURUSD', 'USDCLP', 'GOLD').",
        },
        "timeframe": {
            "type": "string",
            "enum": list(mt5_fuente.TIMEFRAMES),
            "description": "Temporalidad técnica principal para el diagnóstico (por defecto 'H1').",
        },
    },
    requeridos=["simbolo"],
    nombre="analizar_posicion_holistica",
)
def analizar_posicion_holistica(
    simbolo: str,
    timeframe: str = "H1",
) -> dict[str, Any]:
    simbolo_clean = simbolo.strip().upper()

    # 1. Obtener datos de MT5 (Cuenta y Posiciones)
    cuenta = mt5_fuente.cuenta()
    equidad = cuenta.get("equidad") or 1.0

    posiciones_resp = mt5_fuente.posiciones(simbolo=simbolo_clean)
    posiciones_lista = posiciones_resp.get("posiciones", [])

    posicion_activa = posiciones_lista[0] if posiciones_lista else None

    # 2. Análisis Técnico e Indicadores
    ind_tecnicos = analisis_tools.calcular_indicadores_tecnicos(
        simbolo=simbolo_clean, timeframe=timeframe, cantidad=300
    )

    precio_actual = ind_tecnicos.get("precio_actual")
    if not precio_actual:
        precio_info = mt5_fuente.precio(simbolo_clean)
        precio_actual = precio_info.get("ask", 0.0)

    # 3. Evaluación de Riesgo de la Posición
    riesgo_info = None
    if posicion_activa:
        riesgo_resp = analisis_tools.analizar_riesgo_posicion(simbolo=simbolo_clean)
        if riesgo_resp.get("posiciones"):
            riesgo_info = riesgo_resp["posiciones"][0]

    # 4. Contexto Macro / Noticias (Investing + YFinance)
    noticias_list = []
    try:
        inv_res = inv_fuente.buscar_noticias(busqueda=simbolo_clean, categoria="forex", cantidad=3)
        noticias_list.extend(inv_res.get("noticias", []))
    except Exception:
        pass

    if not noticias_list:
        try:
            yf_sym = _mapear_simbolo_yfinance(simbolo_clean)
            yf_news = yf_fuente.noticias(yf_sym, cantidad=3)
            noticias_list.extend(yf_news)
        except Exception:
            pass

    # 5. Generación de Escenarios (Alcista / Neutral / Bajista)
    atr_data = ind_tecnicos.get("indicadores", {}).get("atr_14", {})
    atr_val = atr_data.get("valor_absoluto") or (precio_actual * 0.005)

    point = 0.00001 if "USD" in simbolo_clean and "JPY" not in simbolo_clean else 0.01
    lotes_pos = posicion_activa.get("lotes", 0.1) if posicion_activa else 0.1
    tipo_pos = posicion_activa.get("tipo", "COMPRA") if posicion_activa else "COMPRA"

    mult_tipo = 1.0 if tipo_pos == "COMPRA" else -1.0
    impacto_alcista = round((atr_val * 1.5 / point) * lotes_pos * 10 * point * 10000 * mult_tipo, 2)
    impacto_bajista = round((-atr_val * 1.5 / point) * lotes_pos * 10 * point * 10000 * mult_tipo, 2)

    escenarios = [
        {
            "escenario": "Alcista",
            "condicion_tecnica": f"Supera resistencia a +{round(atr_val * 1.5, 4)}",
            "precio_proyectado": round(precio_actual + (atr_val * 1.5), 5),
            "impacto_estimado_usd": impacto_alcista,
            "accion_sugerida": "Mantener / Buscar TP si es COMPRA; evaluar SL si es VENTA",
        },
        {
            "escenario": "Consolidación / Neutral",
            "condicion_tecnica": f"Mantener rango ±{round(atr_val, 4)}",
            "precio_proyectado": round(precio_actual, 5),
            "impacto_estimado_usd": 0.0,
            "accion_sugerida": "Ajustar Trailing Stop y vigilar ruptura de rango",
        },
        {
            "escenario": "Bajista",
            "condicion_tecnica": f"Quiebre de soporte a -{round(atr_val * 1.5, 4)}",
            "precio_proyectado": round(precio_actual - (atr_val * 1.5), 5),
            "impacto_estimado_usd": impacto_bajista,
            "accion_sugerida": "Evaluar cierre o cobertura si rompe soporte clave",
        },
    ]

    return {
        "fuente": "Módulo Diagnóstico Holístico (MT5 + YFinance + Investing)",
        "simbolo": simbolo_clean,
        "timeframe": timeframe,
        "equidad_cuenta_usd": equidad,
        "posicion_activa": {
            "tiene_posicion_abierta": posicion_activa is not None,
            "detalle_posicion": posicion_activa,
            "analisis_riesgo": riesgo_info,
        },
        "tecnico": ind_tecnicos,
        "noticias_fundamentales": noticias_list[:4],
        "matriz_escenarios": escenarios,
    }