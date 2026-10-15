# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# --------------------------------- INICIO Piña y Jara diario_panel .PY ---------------------------------
# -------------------------------------------------------------------------------------------------------

"""Fachada de la vista Diario (journal de operaciones).

Apunta al paquete `componentes_plataforma/diario/` (tabla, ficha, mini-gráfico, datos y estilos) y reexporta de allí
`renderizar_panel_journal`, la función que dibuja la vista. Existe para que
`from componentes_plataforma.diario_panel import renderizar_panel_journal` (en `aplicacion.py`) siga funcionando
sin cambios. No contiene lógica propia.
"""
from componentes_plataforma.diario import renderizar_panel_journal

__all__ = ["renderizar_panel_journal"]


# -------------------------------------------------------------------------------------------------------
# ----------------------------------- FIN Piña y Jara diario_panel .PY ----------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
