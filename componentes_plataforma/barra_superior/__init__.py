"""
componentes_plataforma/barra_superior
------------------------
Barra de navegación superior del dashboard (estilo terminal de trading).
- Buscador (visual por ahora) en la posición del antiguo logo.
- Íconos de tema y campana de notificaciones (nucleo_agente/notificaciones.py): avisa cuando el agente
  termina de responder aunque el usuario esté en otra sección.
- Usuario a la derecha: al hacer clic en el nombre se despliega un menú
  (perfil / configuración / cerrar sesión) — con <details>, sin recargar.

La barra queda FIJA arriba y a todo el ancho gracias al contenedor
`st.container(key="barra_nav_fija")` de aplicacion.py + su CSS (position: fixed).

Archivos: barra.py (arma la barra), notificaciones.py (campana), chips.py (Capital/Riesgo/Drawdown/Mercado),
datos.py + iconos.json, usuario_menu.html (menú del usuario) y estilos.css.
"""
from componentes_plataforma.barra_superior.barra import renderizar_barra_navegacion

__all__ = ["renderizar_barra_navegacion"]
