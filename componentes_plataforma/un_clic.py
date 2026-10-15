"""Modo One-Click Trading. El código vive en componentes_plataforma/operacion_un_clic/ (registro, estado, ventana, texto
legal y estilos); este archivo se mantiene para que `from componentes_plataforma.un_clic import al_cambiar,
pedir_terminos_si_corresponde, render_modal_terminos` (ticket y aplicacion.py) siga funcionando.
OJO: el modo demo (PEDIR_SIEMPRE) ahora se cambia en componentes_plataforma/operacion_un_clic/registro.py."""
from componentes_plataforma.operacion_un_clic import (PEDIR_SIEMPRE, aceptado, al_cambiar,
                                          pedir_terminos_si_corresponde, render_modal_terminos)

__all__ = ["aceptado", "al_cambiar", "pedir_terminos_si_corresponde", "render_modal_terminos", "PEDIR_SIEMPRE"]
