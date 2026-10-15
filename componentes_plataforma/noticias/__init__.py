"""
componentes_plataforma/noticias
-------------------
Panel de noticias estilo Investing.com:
  - Noticia PRINCIPAL grande + CARRUSEL paginado (‹ ›, de 4 en 4 hasta 20, loop).
  - Al hacer clic en cualquier noticia se abre un MODAL que incrusta el artículo
    directamente en un iframe DENTRO del sitio (st.iframe), sin botón intermedio
    ni pestaña nueva. Las páginas de artículo de Investing responden 200 y no
    envían X-Frame-Options, por eso se dejan incrustar.
Fuente: RSS de Investing.com en español (título, enlace, imagen, fecha).

Archivos: panel.py (arma la página), secciones.py (principal, carrusel, más noticias), modal.py,
tarjetas.py, rss.py (lectura con caché), datos.py + fuentes.json (fuentes y parámetros) y estilos.css.
"""
from componentes_plataforma.noticias.panel import renderizar_panel_noticias

__all__ = ["renderizar_panel_noticias"]
