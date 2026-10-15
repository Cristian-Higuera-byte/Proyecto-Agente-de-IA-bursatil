"""Prueba rápida (desde la raíz del proyecto):  python -m fuentes.investing_fuente"""
from fuentes.investing_fuente import buscar_noticias, noticias

import json

pruebas = (
    ("noticias generales", lambda: noticias("general", 3)),
    ("noticias forex", lambda: noticias("forex", 3)),
    ("buscar_noticias", lambda: buscar_noticias("inflación", "economia", 3)),
)
for nombre, prueba in pruebas:
    print(f"\n=== {nombre}")
    try:
        print(json.dumps(prueba(), ensure_ascii=False, indent=2, default=str))
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
