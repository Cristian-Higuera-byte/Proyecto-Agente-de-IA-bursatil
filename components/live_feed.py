"""Feed de precios EN VIVO del navegador (SSE). El código vive en components/feed/ (servidor, atributos,
inyección y el JavaScript por fragmentos en js/); este archivo se mantiene para que los
`from components.live_feed import intervalo, attrs, inyectar_feed, feed_activo` de todo el proyecto
sigan funcionando."""
from components.feed import API_URL, attrs, feed_activo, inyectar_feed, intervalo

__all__ = ["API_URL", "feed_activo", "intervalo", "attrs", "inyectar_feed"]
