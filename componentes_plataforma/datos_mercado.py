"""Datos de mercado. El código vive en componentes_plataforma/mercado_datos/ (carga, entrada, precios, referencias y
sparkline); este archivo se mantiene para que el `from componentes_plataforma.datos_mercado import ...` de aplicacion.py y los
mercados siga funcionando."""
from componentes_plataforma.mercado_datos import (actualizar_precios_mt5, cargar_datos_mercado, cierre_previo,
                                      construir_entrada, historial_sparkline, variacion)

# Nombres con guion bajo que usaba mercados_panel antes de la separación
_cierre_previo = cierre_previo
_historial_sparkline = historial_sparkline
_variacion = variacion

__all__ = ["cargar_datos_mercado", "actualizar_precios_mt5", "construir_entrada"]
