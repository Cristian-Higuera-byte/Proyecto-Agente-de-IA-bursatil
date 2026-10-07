"""Módulo de análisis cuantitativo, riesgo estadístico y simulación para el agente.

NOMBRE DEL ARCHIVO: herramientas/cuantitativo_tools.py
"""

from __future__ import annotations

import math
import random
from statistics import mean, stdev
from typing import Any

from fuentes import mt5_fuentes as mt5_fuente
from fuentes import yfinance_fuente as yf_fuente
from herramientas.base import herramienta


def _mapear_simbolo_yf(simbolo: str) -> str:
    s = (simbolo or "").strip().upper().replace("/", "")
    if s == "EURUSD": return "EURUSD=X"
    if s == "USDCLP": return "USDCLP=X"
    if s == "GBPUSD": return "GBPUSD=X"
    if s in ("XAUUSD", "GOLD"): return "GC=F"
    if s in ("WTI", "CL"): return "CL=F"
    if s == "BTCUSD": return "BTC-USD"
    if not s.endswith("=X") and len(s) == 6 and s.isalpha():
        return f"{s}=X"
    return s


def _obtener_retornos_historicos(simbolo: str, cantidad: int = 100) -> list[float]:
    """Obtiene serie de retornos porcentuales diarios para un activo."""
    s_clean = simbolo.strip().upper()
    cierres = []
    
    try:
        res = mt5_fuente.velas(simbolo=s_clean, timeframe="D1", cantidad=cantidad, ultimas_velas=cantidad)
        cierres = [v["close"] for v in res.get("ultimas_velas", []) if v.get("close")]
    except Exception:
        pass

    if not cierres or len(cierres) < 10:
        try:
            yf_sym = _mapear_simbolo_yf(s_clean)
            res_yf = yf_fuente.historico(simbolo=yf_sym, periodo="6mo", intervalo="1d", ultimas_velas=cantidad)
            cierres = [v["cierre"] for v in res_yf.get("ultimas_velas", []) if v.get("cierre")]
        except Exception:
            pass

    if len(cierres) < 2:
        return []

    retornos = [(cierres[i] - cierres[i - 1]) / cierres[i - 1] for i in range(1, len(cierres))]
    return retornos


@herramienta(
    descripcion=(
        "Calcula la matriz de correlación de Pearson entre un listado de activos. "
        "Permite identificar sobreexposición o coberturas cruzadas en la cartera."
    ),
    parametros={
        "simbolos": {
            "type": "string",
            "description": "Lista de símbolos separados por coma (ej. 'EURUSD,GBPUSD,GOLD,USDCLP').",
        },
        "cantidad_dias": {
            "type": "integer",
            "description": "Número de días de histórico para el cálculo. Por defecto 90.",
        },
    },
    requeridos=["simbolos"],
    nombre="calcular_matriz_correlacion",
)
def calcular_matriz_correlacion(
    simbolos: str,
    cantidad_dias: int = 90,
) -> dict[str, Any]:
    lista_simbolos = [s.strip().upper() for s in simbolos.split(",") if s.strip()]
    if len(lista_simbolos) < 2:
        return {"error": "Se requieren al menos 2 símbolos para calcular la matriz de correlación."}

    retornos_dict: dict[str, list[float]] = {}
    for sym in lista_simbolos:
        rets = _obtener_retornos_historicos(sym, cantidad=cantidad_dias)
        if rets:
            retornos_dict[sym] = rets

    activos_validos = list(retornos_dict.keys())
    if len(activos_validos) < 2:
        return {"error": "No se obtuvieron suficientes datos históricos para los símbolos indicados."}

    # Alinear longitud de retornos
    min_len = min(len(r) for r in retornos_dict.values())
    for k in activos_validos:
        retornos_dict[k] = retornos_dict[k][-min_len:]

    matriz: dict[str, dict[str, float]] = {}
    alertas_sobreexposicion: list[str] = []

    for s1 in activos_validos:
        matriz[s1] = {}
        r1 = retornos_dict[s1]
        m1 = mean(r1)
        sd1 = stdev(r1) if len(r1) > 1 else 1.0

        for s2 in activos_validos:
            if s1 == s2:
                matriz[s1][s2] = 1.0
                continue

            r2 = retornos_dict[s2]
            m2 = mean(r2)
            sd2 = stdev(r2) if len(r2) > 1 else 1.0

            cov = sum((x - m1) * (y - m2) for x, y in zip(r1, r2)) / (min_len - 1)
            corr = cov / (sd1 * sd2) if (sd1 * sd2) != 0 else 0.0
            corr_round = round(corr, 4)
            matriz[s1][s2] = corr_round

            if s1 < s2 and abs(corr_round) >= 0.80:
                rel = "positiva" if corr_round > 0 else "inversa"
                alertas_sobreexposicion.append(
                    f"Alta correlación {rel} ({corr_round}) entre {s1} y {s2}."
                )

    return {
        "fuente": "Módulo Cuantitativo (Pearson Correlation)",
        "activos_analizados": activos_validos,
        "dias_historicos": min_len,
        "matriz_correlacion": matriz,
        "alertas_sobreexposicion": alertas_sobreexposicion,
    }


@herramienta(
    descripcion=(
        "Ejecuta una simulación de Monte Carlo sobre la equidad de la cartera a N días. "
        "Calcula la distribución de retornos, el peor escenario esperado (Drawdown Máximo) y la probabilidad de pérdida."
    ),
    parametros={
        "dias_proyeccion": {
            "type": "integer",
            "description": "Días a proyectar hacia el futuro (ej. 30). Por defecto 30.",
        },
        "num_simulaciones": {
            "type": "integer",
            "description": "Número de trayectorias a simular (ej. 1000). Por defecto 1000.",
        },
        "capital_inicial": {
            "type": "number",
            "description": "Capital en USD. Si no se especifica, toma la equidad actual de MT5.",
        },
    },
    nombre="simular_monte_carlo_cartera",
)
def simular_monte_carlo_cartera(
    dias_proyeccion: int = 30,
    num_simulaciones: int = 1000,
    capital_inicial: float | None = None,
) -> dict[str, Any]:
    cuenta = mt5_fuente.cuenta()
    capital = capital_inicial or cuenta.get("equidad") or 10000.0

    # Obtener volatilidad y retorno promedio de las posiciones de la cartera
    posiciones = mt5_fuente.posiciones().get("posiciones", [])
    simbolos_cartera = list({p["simbolo"] for p in posiciones}) if posiciones else ["EURUSD"]

    retornos_combinados: list[float] = []
    for s in simbolos_cartera:
        retornos_combinados.extend(_obtener_retornos_historicos(s, cantidad=60))

    if not retornos_combinados:
        mu = 0.0003  # ~0.03% promedio diario por defecto
        sigma = 0.008 # ~0.8% volatilidad diaria por defecto
    else:
        mu = mean(retornos_combinados)
        sigma = stdev(retornos_combinados) if len(retornos_combinados) > 1 else 0.01

    resultados_finales: list[float] = []
    max_drawdowns: list[float] = []

    for _ in range(num_simulaciones):
        patrimonio = capital
        pico = capital
        max_dd = 0.0

        for _ in range(dias_proyeccion):
            r = random.gauss(mu, sigma)
            patrimonio *= (1.0 + r)
            if patrimonio > pico:
                pico = patrimonio
            dd = (pico - patrimonio) / pico if pico > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

        resultados_finales.append(patrimonio)
        max_drawdowns.append(max_dd)

    resultados_finales.sort()
    max_drawdowns.sort()

    pct_5 = round(resultados_finales[int(num_simulaciones * 0.05)], 2)
    mediana = round(resultados_finales[int(num_simulaciones * 0.50)], 2)
    pct_95 = round(resultados_finales[int(num_simulaciones * 0.95)], 2)
    peor_dd_esperado = round(max_drawdowns[int(num_simulaciones * 0.95)] * 100, 2)
    prob_pérdida = round(sum(1 for x in resultados_finales if x < capital) / num_simulaciones * 100, 2)

    return {
        "fuente": "Simulador de Monte Carlo (Geométrico Gaussiano)",
        "capital_inicial_usd": capital,
        "dias_proyeccion": dias_proyeccion,
        "simulaciones_ejecutadas": num_simulaciones,
        "parametros_estimados": {
            "retorno_diario_esperado_pct": round(mu * 100, 4),
            "volatilidad_diaria_pct": round(sigma * 100, 4),
        },
        "proyeccion_patrimonio_usd": {
            "escenario_pesimista_p5": pct_5,
            "escenario_mediana_p50": mediana,
            "escenario_optimista_p95": pct_95,
        },
        "metricas_riesgo_monte_carlo": {
            "max_drawdown_esperado_p95_pct": peor_dd_esperado,
            "probabilidad_capital_menor_inicial_pct": prob_pérdida,
        },
    }


@herramienta(
    descripcion=(
        "Evalúa las métricas institucionales de rendimiento y riesgo de la cartera o historial: "
        "Sharpe Ratio, Sortino Ratio, Profit Factor, Win Rate, y Value at Risk (VaR 95% y 99%)."
    ),
    parametros={
        "tasa_libre_riesgo_anual": {
            "type": "number",
            "description": "Tasa libre de riesgo anualizada (ej. 0.04 para 4%). Por defecto 0.04.",
        },
    },
    nombre="evaluar_metricas_rendimiento",
)
def evaluar_metricas_rendimiento(
    tasa_libre_riesgo_anual: float = 0.04,
) -> dict[str, Any]:
    posiciones = mt5_fuente.posiciones().get("posiciones", [])
    beneficios = [p.get("beneficio", 0.0) for p in posiciones]

    if not beneficios:
        # Si no hay operaciones abiertas, recopilar retornos de activos principales para estimar
        retornos = _obtener_retornos_historicos("EURUSD", cantidad=90)
    else:
        cuenta = mt5_fuente.cuenta()
        capital = cuenta.get("equidad") or 10000.0
        retornos = [b / capital for b in beneficios]

    if not retornos or len(retornos) < 2:
        return {"error": "Sin datos suficientes para calcular métricas cuantitativas."}

    r_diario_rf = tasa_libre_riesgo_anual / 252.0
    m_ret = mean(retornos)
    s_ret = stdev(retornos) if len(retornos) > 1 else 0.0001

    # Sharpe Ratio Anualizado
    sharpe = ((m_ret - r_diario_rf) / s_ret) * math.sqrt(252) if s_ret != 0 else 0.0

    # Sortino Ratio (considera solo volatilidad a la baja)
    retornos_negativos = [r for r in retornos if r < 0]
    s_down = stdev(retornos_negativos) if len(retornos_negativos) > 1 else 0.0001
    sortino = ((m_ret - r_diario_rf) / s_down) * math.sqrt(252) if s_down != 0 else 0.0

    # Win Rate y Profit Factor
    ganadoras = [r for r in retornos if r > 0]
    perdedoras = [abs(r) for r in retornos if r < 0]
    win_rate = (len(ganadoras) / len(retornos)) * 100.0 if retornos else 0.0
    profit_factor = (sum(ganadoras) / sum(perdedoras)) if sum(perdedoras) > 0 else (999.0 if sum(ganadoras) > 0 else 0.0)

    # Value at Risk (VaR Paramétrico 95% y 99%)
    cuenta = mt5_fuente.cuenta()
    capital = cuenta.get("equidad") or 10000.0

    var_95_pct = -(m_ret - (1.645 * s_ret))
    var_99_pct = -(m_ret - (2.326 * s_ret))

    return {
        "fuente": "Evaluador de Métricas Cuantitativas",
        "capital_evaluado_usd": capital,
        "muestra_datos": len(retornos),
        "metricas_ratio": {
            "sharpe_ratio_anualizado": round(sharpe, 2),
            "sortino_ratio_anualizado": round(sortino, 2),
            "profit_factor": round(profit_factor, 2),
            "win_rate_pct": round(win_rate, 2),
        },
        "value_at_risk_1dia": {
            "var_95_pct": round(max(0.0, var_95_pct * 100), 2),
            "var_95_usd": round(max(0.0, var_95_pct * capital), 2),
            "var_99_pct": round(max(0.0, var_99_pct * 100), 2),
            "var_99_usd": round(max(0.0, var_99_pct * capital), 2),
        },
    }