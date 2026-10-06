"""Módulo de herramientas de análisis técnico y gestión de riesgo para el agente.

NOMBRE DEL ARCHIVO: herramientas/analisis_tools.py
"""

from __future__ import annotations

import math
from typing import Any

from fuentes import mt5_fuentes as fuente
from herramientas.base import herramienta


# ──────────────────────────────────────────────────────────────
# Funciones Matemáticas Auxiliares (Sin dependencias externas)
# ──────────────────────────────────────────────────────────────

def _sma(valores: list[float], periodo: int) -> float | None:
    if len(valores) < periodo:
        return None
    return sum(valores[-periodo:]) / periodo


def _ema_serie(valores: list[float], periodo: int) -> list[float]:
    if len(valores) < periodo:
        return []
    k = 2 / (periodo + 1)
    ema_list = [sum(valores[:periodo]) / periodo]
    for v in valores[periodo:]:
        ema_list.append((v * k) + (ema_list[-1] * (1 - k)))
    return ema_list


def _rsi(cierres: list[float], periodo: int = 14) -> float | None:
    if len(cierres) <= periodo:
        return None
    gains, losses = [], []
    for i in range(1, len(cierres)):
        diff = cierres[i] - cierres[i - 1]
        gains.append(max(0.0, diff))
        losses.append(max(0.0, -diff))

    avg_gain = sum(gains[:periodo]) / periodo
    avg_loss = sum(losses[:periodo]) / periodo

    for i in range(periodo, len(gains)):
        avg_gain = (avg_gain * (periodo - 1) + gains[i]) / periodo
        avg_loss = (avg_loss * (periodo - 1) + losses[i]) / periodo

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 2)


def _atr(maximos: list[float], minimos: list[float], cierres: list[float], periodo: int = 14) -> float | None:
    if len(cierres) <= periodo:
        return None
    tr_list = []
    for i in range(1, len(cierres)):
        tr = max(
            maximos[i] - minimos[i],
            abs(maximos[i] - cierres[i - 1]),
            abs(minimos[i] - cierres[i - 1]),
        )
        tr_list.append(tr)

    atr = sum(tr_list[:periodo]) / periodo
    for i in range(periodo, len(tr_list)):
        atr = (atr * (periodo - 1) + tr_list[i]) / periodo
    return atr


def _macd(cierres: list[float], rapida: int = 12, lenta: int = 26, senal: int = 9) -> tuple[float | None, float | None, float | None]:
    if len(cierres) < lenta + senal:
        return None, None, None
    ema_rapida = _ema_serie(cierres, rapida)
    ema_lenta = _ema_serie(cierres, lenta)

    diff_len = len(ema_rapida) - len(ema_lenta)
    macd_line = [r - l for r, l in zip(ema_rapida[diff_len:], ema_lenta)]

    signal_line_list = _ema_serie(macd_line, senal)
    if not signal_line_list:
        return None, None, None

    macd_val = macd_line[-1]
    signal_val = signal_line_list[-1]
    hist_val = macd_val - signal_val
    return macd_val, signal_val, hist_val


def _bollinger(cierres: list[float], periodo: int = 20, desv: float = 2.0) -> tuple[float | None, float | None, float | None]:
    if len(cierres) < periodo:
        return None, None, None
    sub = cierres[-periodo:]
    sma = sum(sub) / periodo
    varianza = sum((x - sma) ** 2 for x in sub) / periodo
    std = math.sqrt(varianza)
    return sma + (desv * std), sma, sma - (desv * std)


# ──────────────────────────────────────────────────────────────
# Herramientas del Agente
# ──────────────────────────────────────────────────────────────

@herramienta(
    descripcion=(
        "Calcula indicadores técnicos clave en tiempo real sobre un activo en MT5: "
        "RSI(14), ATR(14), MACD(12,26,9), Medias Móviles (EMA20, SMA50, SMA200) y Bandas de Bollinger(20,2)."
    ),
    parametros={
        "simbolo": {
            "type": "string",
            "description": "Símbolo del activo en MT5 (ej. 'EURUSD', 'GOLD', 'US500').",
        },
        "timeframe": {
            "type": "string",
            "enum": list(fuente.TIMEFRAMES),
            "description": "Temporalidad para el cálculo (M1, M5, M15, M30, H1, H4, D1). Por defecto 'H1'.",
        },
        "cantidad": {
            "type": "integer",
            "description": "Número de velas históricas a evaluar (mínimo 250 recomendado). Por defecto 300.",
        },
    },
    requeridos=["simbolo"],
    nombre="calcular_indicadores_tecnicos",
)
def calcular_indicadores_tecnicos(
    simbolo: str,
    timeframe: str = "H1",
    cantidad: int = 300,
) -> dict[str, Any]:
    datos_velas = fuente.velas(simbolo=simbolo, timeframe=timeframe, cantidad=cantidad, ultimas_velas=1)
    
    # Extraer arrays de precios históricos
    velas_historicas = fuente.velas(simbolo=simbolo, timeframe=timeframe, cantidad=cantidad, ultimas_velas=cantidad)["ultimas_velas"]
    if not velas_historicas:
        return {"error": f"No se obtuvieron suficientes velas para {simbolo}."}

    cierres = [v["close"] for v in velas_historicas if v["close"] is not None]
    maximos = [v["high"] for v in velas_historicas if v["high"] is not None]
    minimos = [v["low"] for v in velas_historicas if v["low"] is not None]

    precio_actual = cierres[-1]

    # 1. RSI
    rsi_val = _rsi(cierres, 14)
    estado_rsi = "NEUTRAL"
    if rsi_val is not None:
        if rsi_val >= 70:
            estado_rsi = "SOBRECOMPRA"
        elif rsi_val <= 30:
            estado_rsi = "SOBREVENTA"

    # 2. ATR
    atr_val = _atr(maximos, minimos, cierres, 14)

    # 3. MACD
    macd_val, signal_val, hist_val = _macd(cierres)
    sesgo_macd = "NEUTRAL"
    if hist_val is not None:
        sesgo_macd = "ALCISTA" if hist_val > 0 else "BAJISTA"

    # 4. Medias Móviles
    ema_20_list = _ema_serie(cierres, 20)
    ema_20 = round(ema_20_list[-1], 5) if ema_20_list else None

    sma_50_raw = _sma(cierres, 50)
    sma_200_raw = _sma(cierres, 200)
    sma_50 = round(sma_50_raw, 5) if sma_50_raw is not None else None
    sma_200 = round(sma_200_raw, 5) if sma_200_raw is not None else None

    # 5. Bandas de Bollinger
    b_sup, b_med, b_inf = _bollinger(cierres)

    return {
        "fuente": "MetaTrader 5",
        "simbolo": datos_velas["simbolo"],
        "timeframe": timeframe,
        "precio_actual": precio_actual,
        "indicadores": {
            "rsi_14": {
                "valor": rsi_val,
                "diagnostico": estado_rsi,
            },
            "atr_14": {
                "valor_absoluto": round(atr_val, 5) if atr_val else None,
                "volatilidad_pct": round((atr_val / precio_actual) * 100, 2) if atr_val else None,
            },
            "macd_12_26_9": {
                "linea_macd": round(macd_val, 5) if macd_val else None,
                "linea_senal": round(signal_val, 5) if signal_val else None,
                "histograma": round(hist_val, 5) if hist_val else None,
                "sesgo": sesgo_macd,
            },
            "medias_moviles": {
                "ema_20": ema_20,
                "sma_50": sma_50,
                "sma_200": sma_200,
                "precio_vs_sma200": "POR_ENCIMA (Tendencia Alcista)" if (sma_200 and precio_actual > sma_200) else "POR_DEBAJO (Tendencia Bajista)",
            },
            "bandas_bollinger_20_2": {
                "banda_superior": round(b_sup, 5) if b_sup else None,
                "banda_media": round(b_med, 5) if b_med else None,
                "banda_inferior": round(b_inf, 5) if b_inf else None,
            },
        },
    }


@herramienta(
    descripcion=(
        "Analiza detalladamente el riesgo de las posiciones abiertas: calcula la distancia "
        "al Stop Loss y Take Profit (en pips/puntos y en monto monetario $), el porcentaje de "
        "riesgo respecto a la equidad de la cuenta y el Ratio Riesgo:Beneficio (R:R)."
    ),
    parametros={
        "simbolo": {
            "type": "string",
            "description": "Filtrar por símbolo específico (opcional). Si no se indica, evalúa todas las posiciones.",
        },
        "ticket": {
            "type": "integer",
            "description": "Ticket específico de una posición (opcional).",
        },
    },
    nombre="analizar_riesgo_posicion",
)
def analizar_riesgo_posicion(simbolo: str | None = None, ticket: int | None = None) -> dict[str, Any]:
    cuenta_info = fuente.cuenta()
    posiciones_info = fuente.posiciones(simbolo=simbolo)

    equidad = cuenta_info.get("equidad") or 1.0
    posiciones_lista = posiciones_info.get("posiciones", [])

    if ticket:
        posiciones_lista = [p for p in posiciones_lista if p.get("ticket") == ticket]

    diagnosticos = []
    riesgo_total_usd = 0.0

    for pos in posiciones_lista:
        sym = pos["simbolo"]
        tipo = pos["tipo"]
        lotes = pos["lotes"]
        precio_ent = pos["precio_apertura"]
        precio_act = pos["precio_actual"]
        sl = pos["sl"]
        tp = pos["tp"]
        pnl = pos["beneficio"]

        tick_info = fuente.precio(sym)
        point = 0.00001 if "USD" in sym and "JPY" not in sym else 0.01

        # Cálculo de Distancias
        distancia_sl_pips = None
        distancia_tp_pips = None
        riesgo_usd = None
        beneficio_usd = None
        ratio_rr = None
        estado_sl = "SIN STOP LOSS (ALTO RIESGO)"

        if sl and sl > 0:
            pips_sl = abs(precio_ent - sl) / point
            distancia_sl_pips = round(pips_sl, 1)
            
            # Estimación monetaria aproximada del riesgo
            riesgo_usd = round(pips_sl * lotes * 10 * point * 10000, 2)
            riesgo_total_usd += riesgo_usd

            if tipo == "COMPRA":
                estado_sl = "PROTEGIDO EN PROFIT" if sl >= precio_ent else "STOP LOSS ACTIVO"
            else:
                estado_sl = "PROTEGIDO EN PROFIT" if sl <= precio_ent else "STOP LOSS ACTIVO"

        if tp and tp > 0:
            pips_tp = abs(tp - precio_ent) / point
            distancia_tp_pips = round(pips_tp, 1)
            beneficio_usd = round(pips_tp * lotes * 10 * point * 10000, 2)

        if riesgo_usd and beneficio_usd and riesgo_usd > 0:
            ratio_rr = round(beneficio_usd / riesgo_usd, 2)

        riesgo_equidad_pct = round((riesgo_usd / equidad) * 100, 2) if riesgo_usd else None

        diagnosticos.append({
            "ticket": pos["ticket"],
            "simbolo": sym,
            "tipo": tipo,
            "lotes": lotes,
            "precio_apertura": precio_ent,
            "precio_actual": precio_act,
            "pnl_flotante_usd": pnl,
            "stop_loss": sl,
            "take_profit": tp,
            "distancia_sl_pips": distancia_sl_pips,
            "distancia_tp_pips": distancia_tp_pips,
            "riesgo_estimado_usd": riesgo_usd,
            "beneficio_estimado_usd": beneficio_usd,
            "riesgo_equidad_pct": riesgo_equidad_pct,
            "ratio_riesgo_beneficio": ratio_rr,
            "estado_stop_loss": estado_sl,
        })

    return {
        "fuente": "MetaTrader 5",
        "equidad_cuenta_usd": equidad,
        "total_posiciones_analizadas": len(diagnosticos),
        "riesgo_total_acumulado_usd": round(riesgo_total_usd, 2),
        "riesgo_total_equidad_pct": round((riesgo_total_usd / equidad) * 100, 2),
        "posiciones": diagnosticos,
    }