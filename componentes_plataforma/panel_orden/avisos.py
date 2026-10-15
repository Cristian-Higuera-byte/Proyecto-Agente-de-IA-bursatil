"""
panel_orden/avisos.py
--------------------
Aviso flotante (toast) del resultado de la orden: recuadro NARANJA (verde→naranja P&J)
para éxito, rojo para error; se cierra solo a los ~6 s o con la ✕. El JS vive en
estatico/avisos.js y se inyecta en el documento padre una sola vez por resultado
(gracias al `nonce`).
"""
import json

from .interfaz import leer_estatico


def toast_js(mensaje: str, es_error: bool, nonce: str) -> str:
    """Devuelve el <script> listo para components.html(), con el mensaje/estado sustituidos."""
    fondo = ("linear-gradient(135deg,#f85149,#da3633)" if es_error
             else "linear-gradient(135deg,#ff4b4b,#ff8f00)")
    icono = "&#9888;" if es_error else "&#10003;"
    js = (leer_estatico("avisos.js")
          .replace("__FONDO__", fondo)
          .replace("__ICONO__", icono)
          .replace("__NONCE__", json.dumps(str(nonce)))
          .replace("__MSG__", json.dumps(mensaje)))
    return f"<script>\n{js}\n</script>"
