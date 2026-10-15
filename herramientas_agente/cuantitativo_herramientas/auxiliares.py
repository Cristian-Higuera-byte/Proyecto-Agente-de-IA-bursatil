"""Funciones y constantes auxiliares de las herramientas (sin registrar nada)."""
from __future__ import annotations

from fuentes import mt5_fuentes as mt5_fuente
from fuentes import yfinance_fuente as yf_fuente


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
