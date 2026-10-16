# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ----------------------------------- INICIO Piña y Jara __init__ .PY -----------------------------------
# -------------------------------------------------------------------------------------------------------

"""
componentes_plataforma/noticias
-------------------
Paquete del panel de noticias estilo Investing.com. Expone solo `renderizar_panel_noticias`, que dibuja la
página completa; los demás módulos son piezas internas.
  - Noticia PRINCIPAL grande + CARRUSEL paginado (‹ ›, de 4 en 4 hasta 20, loop).
  - Al hacer clic en cualquier noticia se abre un MODAL que incrusta el artículo
    directamente en un iframe DENTRO del sitio (st.iframe), sin botón intermedio
    ni pestaña nueva. Las páginas de artículo de Investing responden 200 y no
    envían X-Frame-Options, por eso se dejan incrustar.
Fuente: RSS de Investing.com en español (título, enlace, imagen, fecha).

Archivos: panel.py (arma la página), secciones.py (principal, carrusel, más noticias), modal.py,
tarjetas.py, rss.py (lectura con caché), datos.py + fuentes.json (fuentes y parámetros) y estilos.css.
"""
# Fachada: reexporta la función que la aplicación llama para pintar la página de noticias
from componentes_plataforma.noticias.panel import renderizar_panel_noticias

# Nombres públicos del paquete
__all__ = ["renderizar_panel_noticias"]


# -------------------------------------------------------------------------------------------------------
# ------------------------------------- FIN Piña y Jara __init__ .PY ------------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
