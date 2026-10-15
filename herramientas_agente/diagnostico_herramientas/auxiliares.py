"""Funciones y constantes auxiliares de las herramientas (sin registrar nada)."""
from __future__ import annotations

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
