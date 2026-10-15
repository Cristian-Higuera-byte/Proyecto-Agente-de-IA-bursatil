"""
Paquete de la Cartera (posiciones abiertas). API pública (la importa aplicacion.py):
  - renderizar_cartera_lista: la lista (va dentro de un fragmento en vivo).
  - render_modal_cerrar: el modal de confirmación de cierre (fuera de los fragmentos).
Submódulos internos: comun (helpers + CSS) · lista · modal · detalle (+ estatico/).
"""
from .lista import renderizar_cartera_lista
from .modal import render_modal_cerrar

__all__ = ["renderizar_cartera_lista", "render_modal_cerrar"]
