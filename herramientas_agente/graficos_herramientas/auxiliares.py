"""Funciones y constantes auxiliares de las herramientas (sin registrar nada)."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import matplotlib
from matplotlib.patches import Rectangle


matplotlib.use("Agg")  # Backend no interactivo para entornos de servidor/dashboard


# Directorio de salida (ruta absoluta: así el dashboard encuentra el archivo
# aunque Streamlit se lance desde otra carpeta que la terminal).
OUTPUT_DIR = os.path.abspath(os.path.join("static", "graficos"))


os.makedirs(OUTPUT_DIR, exist_ok=True)


TIPOS_VALIDOS = ("velas", "lineas", "barras_ohlc", "comparativo")


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


def _etiqueta_fecha(valor: Any, timeframe: str) -> str:
    """Etiqueta legible para el eje X. D1 muestra la fecha; el resto, día-mes y hora."""
    try:
        if isinstance(valor, (int, float)):
            dt = datetime.fromtimestamp(valor)
        else:
            dt = datetime.fromisoformat(str(valor).replace("Z", "").replace("T", " ")[:19])
        return dt.strftime("%Y-%m-%d" if timeframe == "D1" else "%d-%m %H:%M")
    except Exception:
        return str(valor)[-8:]


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
