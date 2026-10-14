"""
Paquete de login. API pública: `requerir_login` (la importa app.py). La UI vive en
pantalla.py y la mecánica de sesión (iniciar/cerrar/restaurar token) en sesion.py.
"""
from .pantalla import requerir_login

__all__ = ["requerir_login"]
