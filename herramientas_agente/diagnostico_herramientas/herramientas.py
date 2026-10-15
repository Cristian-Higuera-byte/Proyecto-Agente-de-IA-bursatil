"""Herramientas registradas para el agente (los esquemas viven en esquemas.json)."""
from __future__ import annotations

from typing import Any

from fuentes import investing_fuente as inv_fuente
from fuentes import mt5_fuentes as mt5_fuente
from fuentes import yfinance_fuente as yf_fuente
from herramientas_agente import analisis_herramientas
from herramientas_agente.base import herramienta
from herramientas_agente.diagnostico_herramientas.auxiliares import _mapear_simbolo_yfinance


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
    ind_tecnicos = analisis_herramientas.calcular_indicadores_tecnicos(
        simbolo=simbolo_clean, timeframe=timeframe, cantidad=300
    )

    precio_actual = ind_tecnicos.get("precio_actual")
    if not precio_actual:
        precio_info = mt5_fuente.precio(simbolo_clean)
        precio_actual = precio_info.get("ask", 0.0)

    # 3. Evaluación de Riesgo de la Posición
    riesgo_info = None
    if posicion_activa:
        riesgo_resp = analisis_herramientas.analizar_riesgo_posicion(simbolo=simbolo_clean)
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

    lotes_pos = posicion_activa.get("lotes", 0.1) if posicion_activa else 0.1
    tipo_pos = posicion_activa.get("tipo", "COMPRA") if posicion_activa else "COMPRA"
    hipotetico = posicion_activa is None   # sin posición abierta se ilustra con 0.1 lotes de compra

    def impacto(precio_destino: float) -> float | None:
        """Resultado en dinero que calcula MT5 si el precio va del actual al proyectado."""
        try:
            return mt5_fuente.resultado_si_precio(simbolo_clean, tipo_pos, lotes_pos, precio_actual, precio_destino)
        except mt5_fuente.ErrorMT5:
            return None

    sube = precio_actual + atr_val * 1.5
    baja = precio_actual - atr_val * 1.5
    escenarios = [
        {
            "escenario": "Alcista",
            "condicion_tecnica": f"Supera resistencia a +{round(atr_val * 1.5, 4)}",
            "precio_proyectado": round(sube, 5),
            "impacto_estimado_usd": impacto(sube),
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
            "precio_proyectado": round(baja, 5),
            "impacto_estimado_usd": impacto(baja),
            "accion_sugerida": "Evaluar cierre o cobertura si rompe soporte clave",
        },
    ]
    nota_escenarios = (
        "Escenarios de referencia basados en 1.5 x ATR (no son predicciones ni tienen probabilidad). "
        + ("Impacto calculado para una posición HIPOTÉTICA de 0.1 lotes de compra: no hay posición abierta."
           if hipotetico else "Impacto calculado sobre la posición abierta, con el cálculo de MT5.")
    )

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
        "nota_escenarios": nota_escenarios,
    }
