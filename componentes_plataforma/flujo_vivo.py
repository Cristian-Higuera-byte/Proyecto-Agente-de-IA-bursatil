"""Feed de precios EN VIVO del navegador (SSE). El código vive en componentes_plataforma/flujo_precios/ (servidor, atributos,
inyección y el JavaScript por fragmentos en js/); este archivo se mantiene para que los
`from componentes_plataforma.flujo_vivo import intervalo, attrs, inyectar_feed, feed_activo` de todo el proyecto
sigan funcionando."""
from componentes_plataforma.flujo_precios import API_URL, attrs, feed_activo, inyectar_feed, intervalo

__all__ = ["API_URL", "feed_activo", "intervalo", "attrs", "inyectar_feed"]
