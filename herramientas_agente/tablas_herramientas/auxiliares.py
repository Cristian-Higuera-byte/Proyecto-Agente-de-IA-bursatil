# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ---------------------------------- INICIO Piña y Jara auxiliares .PY ----------------------------------
# -------------------------------------------------------------------------------------------------------

"""Constantes auxiliares de las herramientas de tablas (sin registrar nada).

Los reportes ya no se guardan en una carpeta común sino en la carpeta privada de cada usuario (`herramientas/archivos_privados.py`)."""
from __future__ import annotations

# Tipos de reporte aceptados (los mismos del enum del esquema).
TIPOS_DE_REPORTE = ("posiciones_abiertas", "riesgo_cartera", "datos_personalizados")
# Formatos aceptados y la extensión con la que se guarda cada uno.
EXTENSION_DE_FORMATO = {"markdown": ".md", "html": ".html", "csv": ".csv"}
# Topes para que unos datos enormes no llenen el disco ni la memoria: filas, columnas, largo de una celda y largo del JSON de entrada.
LIMITES = {"filas": 2000, "columnas": 30, "celda": 1000, "json": 1_000_000}


# -------------------------------------------------------------------------------------------------------
# ------------------------------------ FIN Piña y Jara auxiliares .PY -----------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
