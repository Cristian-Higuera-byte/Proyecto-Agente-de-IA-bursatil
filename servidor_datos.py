"""
servidor_datos.py
-----------------
Lanzador del servidor de datos de MetaTrader 5 (precios en vivo por SSE, velas y órdenes del gráfico).
El código vive en el paquete `servidor_precios/`.

Ejecutar en una terminal APARTE, además del `streamlit run aplicacion.py`:
    env\\Scripts\\python servidor_datos.py
"""
from servidor_precios import ejecutar

if __name__ == "__main__":
    ejecutar()
