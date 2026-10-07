"""Módulo de análisis de estructura de mercado, Price Action y Smart Money Concepts (SMC).

NOMBRE DEL ARCHIVO: herramientas/estructura_mercado_tools.py
"""

from __future__ import annotations

from typing import Any

from fuentes import mt5_fuentes as mt5_fuente
from fuentes import yfinance_fuente as yf_fuente
from herramientas.base import herramienta


def _obtener_velas_historicas(simbolo: str, timeframe: str = "H1", cantidad: int = 100) -> list[dict[str, Any]]:
    s_clean = simbolo.strip().upper()
    velas = []

    try:
        res = mt5_fuente.velas(simbolo=s_clean, timeframe=timeframe, cantidad=cantidad, ultimas_velas=cantidad)
        velas = res.get("ultimas_velas", [])
    except Exception:
        pass

    if not velas:
        try:
            yf_sym = s_clean
            if len(s_clean) == 6 and s_clean.isalpha() and not s_clean.endswith("=X"):
                yf_sym = f"{s_clean}=X"
            elif s_clean in ("XAUUSD", "GOLD"):
                yf_sym = "GC=F"

            tf_yf = "1h" if "H" in timeframe.upper() else "1d"
            res_yf = yf_fuente.historico(simbolo=yf_sym, periodo="1mo", intervalo=tf_yf, ultimas_velas=cantidad)
            for v in res_yf.get("ultimas_velas", []):
                velas.append({
                    "time": v.get("fecha"),
                    "open": v.get("apertura"),
                    "high": v.get("maximo"),
                    "low": v.get("minimo"),
                    "close": v.get("cierre"),
                    "tick_volume": v.get("volumen", 1000),
                })
        except Exception:
            pass

    return velas


@herramienta(
    descripcion=(
        "Detecta soportes y resistencias clave, Swing Highs/Lows y Puntos Pivote institucionales "
        "en un símbolo y temporalidad determinados."
    ),
    parametros={
        "simbolo": {
            "type": "string",
            "description": "Símbolo del activo (ej. 'EURUSD', 'GBPUSD', 'XAUUSD').",
        },
        "timeframe": {
            "type": "string",
            "description": "Temporalidad para el análisis ('M15', 'H1', 'H4', 'D1'). Por defecto 'H1'.",
        },
        "cantidad_velas": {
            "type": "integer",
            "description": "Número de velas para evaluar la estructura. Por defecto 100.",
        },
    },
    requeridos=["simbolo"],
    nombre="detectar_niveles_clave",
)
def detectar_niveles_clave(
    simbolo: str,
    timeframe: str = "H1",
    cantidad_velas: int = 100,
) -> dict[str, Any]:
    velas = _obtener_velas_historicas(simbolo, timeframe=timeframe, cantidad=cantidad_velas)
    if not velas or len(velas) < 10:
        return {"error": f"Sin datos suficientes para detectar niveles clave en {simbolo}."}

    v_ref = velas[-2] if len(velas) > 1 else velas[-1]
    h, l, c = v_ref.get("high", 0.0), v_ref.get("low", 0.0), v_ref.get("close", 0.0)

    pivot = (h + l + c) / 3.0
    r1 = (2 * pivot) - l
    s1 = (2 * pivot) - h
    r2 = pivot + (h - l)
    s2 = pivot - (h - l)

    swing_highs: list[float] = []
    swing_lows: list[float] = []

    for i in range(2, len(velas) - 2):
        v_curr = velas[i]
        if (
            v_curr["high"] > velas[i - 1]["high"]
            and v_curr["high"] > velas[i - 2]["high"]
            and v_curr["high"] > velas[i + 1]["high"]
            and v_curr["high"] > velas[i + 2]["high"]
        ):
            swing_highs.append(round(v_curr["high"], 5))

        if (
            v_curr["low"] < velas[i - 1]["low"]
            and v_curr["low"] < velas[i - 2]["low"]
            and v_curr["low"] < velas[i + 1]["low"]
            and v_curr["low"] < velas[i + 2]["low"]
        ):
            swing_lows.append(round(v_curr["low"], 5))

    precio_actual = velas[-1].get("close", 0.0)

    return {
        "fuente": "Extractor de Estructura y Niveles Clave (Price Action)",
        "simbolo": simbolo.upper(),
        "timeframe": timeframe.upper(),
        "precio_actual": precio_actual,
        "puntos_pivote_clasicos": {
            "pivot": round(pivot, 5),
            "resistencia_1": round(r1, 5),
            "resistencia_2": round(r2, 5),
            "soporte_1": round(s1, 5),
            "soporte_2": round(s2, 5),
        },
        "swing_highs_recientes": swing_highs[-3:],
        "swing_lows_recientes": swing_lows[-3:],
    }


@herramienta(
    descripcion=(
        "Identifica desbalances de precio (Fair Value Gaps - FVG) e ineficiencias, "
        "así como Order Blocks (bloques de órdenes institucionales) alcistas y bajistas."
    ),
    parametros={
        "simbolo": {
            "type": "string",
            "description": "Símbolo a analizar (ej. 'EURUSD', 'XAUUSD').",
        },
        "timeframe": {
            "type": "string",
            "description": "Temporalidad ('M15', 'H1', 'H4'). Por defecto 'H1'.",
        },
        "cantidad_velas": {
            "type": "integer",
            "description": "Cantidad de velas históricas a escanear. Por defecto 60.",
        },
    },
    requeridos=["simbolo"],
    nombre="identificar_order_blocks_fvg",
)
def identificar_order_blocks_fvg(
    simbolo: str,
    timeframe: str = "H1",
    cantidad_velas: int = 60,
) -> dict[str, Any]:
    velas = _obtener_velas_historicas(simbolo, timeframe=timeframe, cantidad=cantidad_velas)
    if not velas or len(velas) < 5:
        return {"error": f"Datos insuficientes para escanear FVG u Order Blocks en {simbolo}."}

    fvgs: list[dict[str, Any]] = []
    order_blocks: list[dict[str, Any]] = []

    for i in range(len(velas) - 3, 0, -1):
        v1, v2, v3 = velas[i - 1], velas[i], velas[i + 1]

        if v3["low"] > v1["high"]:
            fvgs.append({
                "tipo": "FVG_ALCISTA",
                "rango_inferior": round(v1["high"], 5),
                "rango_superior": round(v3["low"], 5),
                "vela_index": i,
                "timestamp": v2.get("time"),
            })

        elif v3["high"] < v1["low"]:
            fvgs.append({
                "tipo": "FVG_BAJISTA",
                "rango_inferior": round(v3["high"], 5),
                "rango_superior": round(v1["low"], 5),
                "vela_index": i,
                "timestamp": v2.get("time"),
            })

    for i in range(2, len(velas) - 2):
        cuerpo = abs(velas[i]["close"] - velas[i]["open"])
        cuerpo_siguiente = abs(velas[i + 1]["close"] - velas[i + 1]["open"])

        if velas[i]["close"] < velas[i]["open"] and velas[i + 1]["close"] > velas[i + 1]["open"] and cuerpo_siguiente > cuerpo * 1.8:
            order_blocks.append({
                "tipo": "ORDER_BLOCK_ALCISTA",
                "zona_high": round(velas[i]["high"], 5),
                "zona_low": round(velas[i]["low"], 5),
                "timestamp": velas[i].get("time"),
            })
        elif velas[i]["close"] > velas[i]["open"] and velas[i + 1]["close"] < velas[i + 1]["open"] and cuerpo_siguiente > cuerpo * 1.8:
            order_blocks.append({
                "tipo": "ORDER_BLOCK_BAJISTA",
                "zona_high": round(velas[i]["high"], 5),
                "zona_low": round(velas[i]["low"], 5),
                "timestamp": velas[i].get("time"),
            })

    precio_actual = velas[-1].get("close", 0.0)

    return {
        "fuente": "Detector de Smart Money Concepts (FVG & Order Blocks)",
        "simbolo": simbolo.upper(),
        "timeframe": timeframe.upper(),
        "precio_actual": precio_actual,
        "fvg_detectados": fvgs[:5],
        "order_blocks_detectados": order_blocks[-5:],
    }


@herramienta(
    descripcion=(
        "Calcula el perfil de volumen acumulado (Point of Control - POC, Value Area High - VAH, "
        "Value Area Low - VAL) para identificar las zonas de mayor liquidez transaccionada."
    ),
    parametros={
        "simbolo": {
            "type": "string",
            "description": "Símbolo del activo a evaluar (ej. 'EURUSD', 'USDCLP').",
        },
        "timeframe": {
            "type": "string",
            "description": "Temporalidad ('M15', 'H1', 'D1'). Por defecto 'H1'.",
        },
        "cantidad_velas": {
            "type": "integer",
            "description": "Número de velas para construir el perfil de volumen. Por defecto 100.",
        },
        "niveles_precio": {
            "type": "integer",
            "description": "Número de franjas/bins de precio. Por defecto 24.",
        },
    },
    requeridos=["simbolo"],
    nombre="calcular_perfil_volumen",
)
def calcular_perfil_volumen(
    simbolo: str,
    timeframe: str = "H1",
    cantidad_velas: int = 100,
    niveles_precio: int = 24,
) -> dict[str, Any]:
    velas = _obtener_velas_historicas(simbolo, timeframe=timeframe, cantidad=cantidad_velas)
    if not velas or len(velas) < 10:
        return {"error": f"Sin datos para calcular el Perfil de Volumen en {simbolo}."}

    max_p = max(v["high"] for v in velas)
    min_p = min(v["low"] for v in velas)

    if max_p == min_p:
        return {"error": "El rango de precio es plano en la muestra seleccionada."}

    paso = (max_p - min_p) / niveles_precio
    bins = [0.0] * niveles_precio

    for v in velas:
        p_medio = (v["high"] + v["low"]) / 2.0
        vol = v.get("tick_volume", 100.0)
        idx = min(int((p_medio - min_p) / paso), niveles_precio - 1)
        bins[idx] += vol

    max_vol_idx = max(range(niveles_precio), key=lambda i: bins[i])
    poc_precio = min_p + (max_vol_idx + 0.5) * paso

    vol_total = sum(bins)
    vol_objetivo = vol_total * 0.70

    vol_acum = bins[max_vol_idx]
    idx_low, idx_high = max_vol_idx, max_vol_idx

    while vol_acum < vol_objetivo and (idx_low > 0 or idx_high < niveles_precio - 1):
        v_below = bins[idx_low - 1] if idx_low > 0 else -1
        v_above = bins[idx_high + 1] if idx_high < niveles_precio - 1 else -1

        if v_above >= v_below:
            idx_high += 1
            vol_acum += bins[idx_high]
        else:
            idx_low -= 1
            vol_acum += bins[idx_low]

    val_precio = min_p + idx_low * paso
    vah_precio = min_p + (idx_high + 1) * paso

    return {
        "fuente": "Perfil de Volumen Institucional (Volume Profile)",
        "simbolo": simbolo.upper(),
        "timeframe": timeframe.upper(),
        "velas_analizadas": len(velas),
        "rango_precio": {
            "minimo_rango": round(min_p, 5),
            "maximo_rango": round(max_p, 5),
        },
        "volume_profile_key_levels": {
            "poc_point_of_control": round(poc_precio, 5),
            "vah_value_area_high": round(vah_precio, 5),
            "val_value_area_low": round(val_precio, 5),
        },
        "distribucion_volumen_pct_value_area": round((vol_acum / vol_total) * 100, 2),
    }