"""Funciones y constantes auxiliares de las herramientas (sin registrar nada)."""
from __future__ import annotations

from typing import Any

from fuentes import mt5_fuentes as mt5_fuente
from fuentes import yfinance_fuente as yf_fuente


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
