# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ----------------------------------- INICIO Piña y Jara imagenes .PY -----------------------------------
# -------------------------------------------------------------------------------------------------------

"""Archivos que una herramienta guardó para el usuario (imágenes y reportes), a partir de su resultado (campo 'archivo_guardado').

Un resultado de herramienta es un dato que no se puede dar por confiable (puede traer una ruta cualquiera). Por eso solo se acepta una ruta si, ya resuelta, está dentro de la carpeta PRIVADA del
usuario de la consulta, es un archivo normal, tiene la extensión esperada y no es demasiado grande (herramientas/archivos_privados.py): una ruta fuera de ese espacio, de otro usuario o que
llegue por un enlace simbólico se ignora (V17 de la auditoría)."""
from __future__ import annotations

import json
from typing import Any

from herramientas import archivos_privados

# Extensiones de archivo que se consideran imagen mostrable en el chat y las de los reportes descargables.
_EXT_IMAGEN = archivos_privados.EXTENSIONES_IMAGEN
_EXT_REPORTE = archivos_privados.EXTENSIONES_REPORTE


# TITULO BUSCAR RUTAS

def _buscar_rutas(dato: Any, rutas: list, extensiones: tuple, usuario_id=None) -> None:
    """Busca de forma recursiva el campo 'archivo_guardado' en un resultado y anota solo las rutas que `archivos_privados` autoriza para ese usuario y esas extensiones."""
    # En un diccionario se revisa su propio campo y luego se desciende a sus valores anidados.
    if isinstance(dato, dict):
        ruta = dato.get("archivo_guardado")
        if isinstance(ruta, str):
            real = archivos_privados.ruta_autorizada(ruta, usuario_id, extensiones)
            if real is not None and str(real) not in rutas:
                rutas.append(str(real))
        for valor in dato.values():
            if isinstance(valor, (dict, list)):
                _buscar_rutas(valor, rutas, extensiones, usuario_id)
    elif isinstance(dato, list):
        for valor in dato:
            _buscar_rutas(valor, rutas, extensiones, usuario_id)


# TITULO BUSCAR RUTAS IMAGEN

def _buscar_rutas_imagen(dato: Any, rutas: list, usuario_id=None) -> None:
    """Como `_buscar_rutas` para imágenes (se conserva el nombre original)."""
    _buscar_rutas(dato, rutas, _EXT_IMAGEN, usuario_id)


# TITULO RUTAS DE RESULTADO

def _rutas_de_resultado(resultado: Any, extensiones: tuple, usuario_id=None) -> list:
    """Rutas autorizadas de un resultado de herramienta (texto JSON, dict o lista); lista vacía si no se puede interpretar."""
    # El resultado de la herramienta suele ser un JSON en texto.
    try:
        datos = json.loads(resultado) if isinstance(resultado, str) else resultado
    except (TypeError, ValueError):
        return []
    rutas: list = []
    _buscar_rutas(datos, rutas, extensiones, usuario_id)
    return rutas


# TITULO IMAGENES DE RESULTADO

def imagenes_de_resultado(resultado: Any, usuario_id=None) -> list:
    """Devuelve las rutas de imágenes que una herramienta guardó para el usuario, a partir de su resultado.

    Recibe el resultado como texto JSON, dict o lista; si no se puede interpretar devuelve []. Solo incluye rutas AUTORIZADAS: dentro de la carpeta privada del usuario (`usuario_id`, o el de la
    consulta en curso si no se indica), archivos normales de imagen y de tamaño razonable.
    """
    return _rutas_de_resultado(resultado, _EXT_IMAGEN, usuario_id)


# TITULO ARCHIVOS DE RESULTADO

def archivos_de_resultado(resultado: Any, usuario_id=None) -> list:
    """Como `imagenes_de_resultado`, pero para los reportes descargables (.md, .html y .csv) que una herramienta guardó para el usuario."""
    return _rutas_de_resultado(resultado, _EXT_REPORTE, usuario_id)


# -------------------------------------------------------------------------------------------------------
# ------------------------------------- FIN Piña y Jara imagenes .PY ------------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
