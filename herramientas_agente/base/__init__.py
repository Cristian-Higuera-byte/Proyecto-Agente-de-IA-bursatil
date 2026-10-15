"""Registro de herramientas del agente.

Cada herramienta es una función Python normal, decorada con @herramienta.
El agente no conoce ninguna herramienta en particular: solo pide al registro
sus esquemas (para enviarlos al modelo) y le pasa las llamadas a ejecutar().

Reglas para escribir herramientas:
  * Devolver datos serializables a JSON (dict, list, str, números).
  * Si algo falla, basta con lanzar una excepción: el registro la convierte en
    {"error": ...} para que el modelo pueda corregir o explicarlo al usuario.

Archivos: registro.py (Herramienta, RegistroHerramientas, REGISTRO), decorador.py (@herramienta) y esquemas.py
(cargar_json: lee el esquemas.json de cada paquete de herramientas).
"""
from herramientas_agente.base.decorador import herramienta
from herramientas_agente.base.esquemas import cargar_json
from herramientas_agente.base.registro import (  # noqa: F401
    MAX_CHARS_RESULTADO,
    REGISTRO,
    Herramienta,
    RegistroHerramientas,
    _a_json,
)
