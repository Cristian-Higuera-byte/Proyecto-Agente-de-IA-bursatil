"""
aplicacion.py
-------------
Lanzador del dashboard interactivo de Piña & Jara - Financial Terminal.

    streamlit run aplicacion.py

El código de la página vive en el paquete `aplicacion_principal/`.
"""
import os
import sys

# Asegurar ruta raíz
_raiz = os.path.abspath(os.path.dirname(__file__))
if _raiz not in sys.path:
    sys.path.append(_raiz)

from aplicacion_principal.entorno import corregir_certificado_ssl, importar_consola

corregir_certificado_ssl()
consola = importar_consola()   # lógica del backend (consola_agente.py); None si no está disponible

from aplicacion_principal.pagina import ejecutar

ejecutar(consola)
