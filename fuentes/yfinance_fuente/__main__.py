"""Prueba rápida (desde la raíz del proyecto):  python -m fuentes.yfinance_fuente"""
from fuentes.yfinance_fuente import (buscar, consenso_analistas, cotizacion, estados_financieros, fundamentales,
                                     historico, noticias)

import json

pruebas = (
    ("buscar", lambda: buscar("apple", 3)),
    ("cotizacion", lambda: cotizacion("AAPL")),
    ("historico", lambda: historico("EURUSD=X", "1mo", ultimas_velas=3)),
    ("fundamentales", lambda: fundamentales("AAPL")),
    ("estados_financieros", lambda: estados_financieros("AAPL", "resultados", "anual", 2)),
    ("noticias", lambda: noticias("AAPL", 3)),
    ("consenso_analistas", lambda: consenso_analistas("AAPL")),
)
for nombre, prueba in pruebas:
    print(f"\n=== {nombre}")
    try:
        print(json.dumps(prueba(), ensure_ascii=False, indent=2, default=str))
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {type(e).__name__}: {e}")
