"""Módulo de generación de gráficos bursátiles profesionales para el agente.

NOMBRE DEL ARCHIVO: herramientas/graficos_tools.py
"""

from __future__ import annotations

import base64
import io
import os
from datetime import datetime
from typing import Any

import matplotlib
matplotlib.use("Agg")  # Backend no interactivo para entornos de servidor/dashboard
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from fuentes import mt5_fuentes as mt5_fuente
from fuentes import yfinance_fuente as yf_fuente
from herramientas import analisis_tools
from herramientas.base import herramienta

# Directorio de salida para gráficos descargables
OUTPUT_DIR = os.path.join("static", "graficos")
os.makedirs(OUTPUT_DIR, exist_ok=True)


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


def _dibujar_velas(ax, df_velas: list[dict[str, Any]]):
    """Dibuja velas japonesas personalizadas con mechas y cuerpos alcistas/bajistas."""
    for i, v in enumerate(df_velas):
        o, h, l, c = v["open"], v["high"], v["low"], v["close"]
        color = "#00B0FF" if c >= o else "#FF5252"  # Azul alcista, Rojo bajista
        
        # Mecha
        ax.plot([i, i], [l, h], color=color, linewidth=1.0)
        # Cuerpo
        altura = max(abs(c - o), (h - l) * 0.001)
        bottom = min(o, c)
        rect = Rectangle((i - 0.35, bottom), 0.7, altura, facecolor=color, edgecolor=color, alpha=0.9)
        ax.add_patch(rect)


@herramienta(
    descripcion=(
        "Genera gráficos bursátiles profesionales en alta resolución (PNG y Base64 descargables). "
        "Admite tipos: 'velas' (Candlestick + Volumen + RSI/MACD), 'lineas' (Tendencia/Cierres), "
        "'barras_ohlc' (Barras tradicionales) y 'comparativo' (Rendimiento % relativo entre múltiples activos)."
    ),
    parametros={
        "simbolo": {
            "type": "string",
            "description": "Símbolo principal (ej. 'EURUSD', 'GOLD', 'USDCLP', 'AAPL').",
        },
        "tipo_grafico": {
            "type": "string",
            "enum": ["velas", "lineas", "barras_ohlc", "comparativo"],
            "description": "Tipo de gráfico bursátil a generar. Por defecto 'velas'.",
        },
        "timeframe": {
            "type": "string",
            "enum": list(mt5_fuente.TIMEFRAMES),
            "description": "Temporalidad para las velas (M1, M5, M15, M30, H1, H4, D1). Por defecto 'H1'.",
        },
        "cantidad_velas": {
            "type": "integer",
            "description": "Número de velas a graficar (ej. 50 a 200). Por defecto 80.",
        },
        "comparar_con": {
            "type": "string",
            "description": "Símbolos adicionales separados por coma para gráfico comparativo (ej. 'GBPUSD,USDCLP').",
        },
    },
    requeridos=["simbolo"],
    nombre="generar_grafico_financiero",
)
def generar_grafico_financiero(
    simbolo: str,
    tipo_grafico: str = "velas",
    timeframe: str = "H1",
    cantidad_velas: int = 80,
    comparar_con: str | None = None,
) -> dict[str, Any]:
    simbolo_clean = simbolo.strip().upper()
    n_velas = max(20, min(int(cantidad_velas), 300))

    # Obtener velas desde MT5 o YFinance
    velas_data = []
    try:
        mt5_res = mt5_fuente.velas(simbolo=simbolo_clean, timeframe=timeframe, cantidad=n_velas, ultimas_velas=n_velas)
        velas_data = mt5_res.get("ultimas_velas", [])
    except Exception:
        pass

    if not velas_data:
        try:
            yf_sym = _mapear_simbolo_yf(simbolo_clean)
            yf_res = yf_fuente.historico(simbolo=yf_sym, periodo="1mo", intervalo="1d", ultimas_velas=n_velas)
            for v in yf_res.get("ultimas_velas", []):
                velas_data.append({
                    "time": v["fecha"],
                    "open": v["apertura"],
                    "high": v["maximo"],
                    "low": v["minimo"],
                    "close": v["cierre"],
                    "tick_volume": v["volumen"] or 0,
                })
        except Exception as e:
            return {"error": f"No se pudieron obtener datos históricos para graficar {simbolo_clean}: {e}"}

    if not velas_data:
        return {"error": f"Sin datos disponibles para graficar {simbolo_clean}."}

    # Configuración de Estilo Oscuro Institucional
    plt.style.use("dark_background")
    fig = plt.figure(figsize=(12, 7), dpi=120)
    fig.patch.set_facecolor("#12141D")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"chart_{simbolo_clean}_{tipo_grafico}_{timestamp}.png"
    filepath = os.path.join(OUTPUT_DIR, filename)

    # ──────────────────────────────────────────────────────────
    # 1. Gráfico Comparativo de Rendimiento % Relativo
    # ──────────────────────────────────────────────────────────
    if tipo_grafico == "comparativo" and comparar_con:
        ax = fig.add_subplot(111)
        ax.set_facecolor("#1A1D29")
        
        activos = [simbolo_clean] + [s.strip().upper() for s in comparar_con.split(",") if s.strip()]
        for act in activos:
            try:
                data_act = mt5_fuente.velas(simbolo=act, timeframe=timeframe, cantidad=n_velas, ultimas_velas=n_velas)
                cierres = [v["close"] for v in data_act.get("ultimas_velas", []) if v.get("close")]
                if cierres:
                    base = cierres[0]
                    rend_pct = [((c / base) - 1.0) * 100.0 for c in cierres]
                    ax.plot(rend_pct, label=f"{act} (%)", linewidth=2.0)
            except Exception:
                continue

        ax.axhline(0, color="#888888", linestyle="--", alpha=0.6)
        ax.set_title(f"Rendimiento Relativo % ({', '.join(activos)}) - {timeframe}", color="#FFFFFF", fontsize=14, pad=15)
        ax.set_ylabel("Variación Porcentual (%)", color="#CCCCCC")
        ax.legend(loc="upper left")
        ax.grid(True, color="#2A2E3D", linestyle=":", alpha=0.7)

    # ──────────────────────────────────────────────────────────
    # 2. Gráfico de Velas / Barras OHLC / Líneas con Indicadores
    # ──────────────────────────────────────────────────────────
    else:
        gs = fig.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.15)
        ax_main = fig.add_subplot(gs[0])
        ax_sub = fig.add_subplot(gs[1], sharex=ax_main)

        ax_main.set_facecolor("#1A1D29")
        ax_sub.set_facecolor("#1A1D29")

        cierres = [v["close"] for v in velas_data]
        fechas_str = [str(v.get("time", i))[-8:] for i, v in enumerate(velas_data)]
        indices = list(range(len(velas_data)))

        if tipo_grafico == "velas":
            _dibujar_velas(ax_main, velas_data)
        elif tipo_grafico == "lineas":
            ax_main.plot(indices, cierres, color="#00B0FF", linewidth=2.0, label="Precio Cierre")
            ax_main.fill_between(indices, cierres, min(cierres), color="#00B0FF", alpha=0.15)
        elif tipo_grafico == "barras_ohlc":
            for i, v in enumerate(velas_data):
                color = "#00B0FF" if v["close"] >= v["open"] else "#FF5252"
                ax_main.plot([i, i], [v["low"], v["high"]], color=color, linewidth=1.2)
                ax_main.plot([i - 0.2, i], [v["open"], v["open"]], color=color, linewidth=1.2)
                ax_main.plot([i, i + 0.2], [v["close"], v["close"]], color=color, linewidth=1.2)

        # Superposición de Medias Móviles (EMA20 y SMA50)
        if len(cierres) >= 20:
            ema20 = analisis_tools._ema_serie(cierres, 20)
            ax_main.plot(indices[-len(ema20):], ema20, color="#FFB300", linewidth=1.3, label="EMA 20")
        if len(cierres) >= 50:
            sma50 = [analisis_tools._sma(cierres[:i+1], 50) for i in range(49, len(cierres))]
            ax_main.plot(indices[-len(sma50):], sma50, color="#E040FB", linewidth=1.3, label="SMA 50")

        # Panel Inferior: Oscilador RSI(14)
        rsi_val = analisis_tools._rsi(cierres, 14)
        rsl_series = []
        for i in range(14, len(cierres) + 1):
            r = analisis_tools._rsi(cierres[:i], 14)
            if r is not None:
                rsl_series.append(r)
        
        if rsl_series:
            ax_sub.plot(indices[-len(rsl_series):], rsl_series, color="#00E676", linewidth=1.4, label="RSI (14)")
            ax_sub.axhline(70, color="#FF5252", linestyle="--", alpha=0.7, linewidth=0.8)
            ax_sub.axhline(30, color="#00B0FF", linestyle="--", alpha=0.7, linewidth=0.8)
            ax_sub.fill_between(indices[-len(rsl_series):], rsl_series, 70, where=[x >= 70 for x in rsl_series], color="#FF5252", alpha=0.3)
            ax_sub.fill_between(indices[-len(rsl_series):], rsl_series, 30, where=[x <= 30 for x in rsl_series], color="#00B0FF", alpha=0.3)
            ax_sub.set_ylim(10, 90)

        # Configuración de Ejes y Leyendas
        ax_main.set_title(f"Análisis Bursátil Professional: {simbolo_clean} ({timeframe})", color="#FFFFFF", fontsize=13, pad=12)
        ax_main.legend(loc="upper left", facecolor="#12141D", edgecolor="#2A2E3D")
        ax_main.grid(True, color="#2A2E3D", linestyle=":", alpha=0.6)
        ax_sub.grid(True, color="#2A2E3D", linestyle=":", alpha=0.6)
        
        # Etiquetar fechas en eje X
        paso = max(1, len(indices) // 8)
        ax_sub.set_xticks(indices[::paso])
        ax_sub.set_xticklabels(fechas_str[::paso], rotation=30, ha="right", color="#AAAAAA")
        plt.setp(ax_main.get_xticklabels(), visible=False)

    plt.tight_layout()

    # Guardar a archivo físico y convertir a Base64
    fig.savefig(filepath, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
    
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
    buf.seek(0)
    base64_img = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)

    web_path = f"/static/graficos/{filename}"

    return {
        "fuente": "Generador Visual Bursátil (Matplotlib)",
        "simbolo": simbolo_clean,
        "tipo_grafico": tipo_grafico,
        "timeframe": timeframe,
        "archivo_guardado": filepath,
        "url_descarga": web_path,
        "imagen_base64": f"data:image/png;base64,{base64_img}",
        "mensaje": f"Gráfico {tipo_grafico} generado exitosamente para {simbolo_clean}. Disponible para visualización y descarga.",
    }