"""Actualización LIGERA de precios de la watchlist desde MT5 (tick en vivo)."""
import streamlit as st

from componentes_plataforma.mercado_datos.referencias import variacion
from componentes_plataforma.mercado_datos.sparkline import asegurar_semilla, empujar_spark
from herramientas.puente_mt5 import inicializar_mt5, obtener_precio_actual


def actualizar_precios_mt5():
    """Actualización LIGERA de precios de la watchlist desde MT5 (tick en vivo).
    Usa el nombre EXACTO del símbolo (con '...') — sin limpiarlo."""
    inicializar_mt5()
    datos = st.session_state.get("datos_mercado_real")
    if not datos:
        return
    for simbolo in list(datos.keys()):
        try:
            info_tick = obtener_precio_actual(simbolo)
            if "error" in info_tick:
                continue
            precio_actual = info_tick.get("last", 0) if info_tick.get("last", 0) > 0 else info_tick.get("bid", 0)
            if precio_actual and precio_actual > 0:
                precio_anterior = datos[simbolo].get("precio", precio_actual)
                cambio = precio_actual - precio_anterior
                porcentaje = (cambio / precio_anterior * 100) if precio_anterior else 0.0
                decimales = 2 if precio_actual > 100 else 5
                datos[simbolo]["precio"] = precio_actual
                var = variacion(simbolo, precio_actual, decimales)
                if var:                                   # variación del día
                    datos[simbolo]["var"], datos[simbolo]["sube"] = var
                else:                                     # sin referencia: vs. tick anterior
                    datos[simbolo]["sube"] = cambio >= 0
                    if cambio != 0:
                        datos[simbolo]["var"] = f"{cambio:+.{decimales}f} ({porcentaje:+.2f}%)"
                asegurar_semilla(simbolo)   # símbolos agregados después de la carga
                empujar_spark(simbolo, precio_actual)
        except Exception:
            pass
