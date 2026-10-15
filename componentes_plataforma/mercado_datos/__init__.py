"""
componentes_plataforma/mercado_datos
------------------------
Datos de mercado en sesión (watchlist, índices globales, variación del día y sparklines), separados por
responsabilidad:
  carga.py        carga inicial (indices_globales.json + watchlist del usuario)
  entrada.py      entrada de un símbolo (nombre, categoría, precio, variación)
  precios.py      actualización ligera de precios con el tick de MT5
  referencias.py  cierre diario anterior y variación del día
  sparkline.py    semilla M1 y buffer del mini-gráfico
"""
from componentes_plataforma.mercado_datos.carga import cargar_datos_mercado
from componentes_plataforma.mercado_datos.entrada import construir_entrada
from componentes_plataforma.mercado_datos.precios import actualizar_precios_mt5
from componentes_plataforma.mercado_datos.referencias import cierre_previo, variacion
from componentes_plataforma.mercado_datos.sparkline import historial_sparkline

__all__ = ["cargar_datos_mercado", "construir_entrada", "actualizar_precios_mt5", "cierre_previo", "variacion",
           "historial_sparkline"]
