# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ------------------------------------ INICIO Piña y Jara datos .PY -------------------------------------
# -------------------------------------------------------------------------------------------------------

"""Datos de las secciones «Mercados» y «Noticias» de la portada pública.

Noticias: reutiliza el lector de RSS de la plataforma (componentes_plataforma/noticias/rss.py), que usa fuentes gratuitas y sin inicio de sesión; la portada nunca espera a la red:
si todavía no hay titulares cargados devuelve una lista vacía y la sección muestra un aviso.

Cotizaciones: la fuente de precios de la portada TODAVÍA NO ESTÁ DECIDIDA. Mientras tanto se muestran cotizaciones de ejemplo (`ejemplo=True`, y la sección lo avisa). Para conectar una fuente
real basta con implementar `_cotizaciones_en_vivo()` (devolver la misma lista de diccionarios, con `ejemplo=False`) y la sección deja de mostrar el aviso; el resto del código no cambia.
"""
from __future__ import annotations

# Cotizaciones de ejemplo (símbolo, nombre, precio, variación en %, decimales). Son ilustrativas: no vienen de ningún mercado.
_EJEMPLO = [
    ("EURUSD", "Euro / Dólar", 1.11362, -0.17, 5),
    ("GBPUSD", "Libra / Dólar", 1.33267, 0.00, 5),
    ("USDJPY", "Dólar / Yen", 157.85, 0.01, 2),
    ("GOLD", "Oro", 4023.54, -0.76, 2),
    ("BTCUSD", "Bitcoin", 80175.25, -1.30, 2),
    ("ETHUSD", "Ethereum", 2322.05, -1.44, 2),
    ("US30", "Dow Jones", 52390.00, -0.28, 2),
    ("ACN", "Accenture", 244.89, 0.51, 2),
]


# TITULO COTIZACIONES EN VIVO

def _cotizaciones_en_vivo() -> list[dict] | None:
    """Punto de conexión de la fuente real de precios. Devuelve la lista de cotizaciones (mismas claves que `_ejemplo`, con `ejemplo=False`) o None si no hay fuente configurada.

    Hoy devuelve None: la fuente (por ejemplo Capital.com con una cuenta de servicio, yfinance con retraso, o un proveedor con plan gratuito) está por decidirse."""
    return None


# TITULO EJEMPLO

def _ejemplo() -> list[dict]:
    """Cotizaciones de ejemplo como lista de diccionarios: simbolo, nombre, precio, var (en %), decimales y ejemplo=True."""
    return [{"simbolo": s, "nombre": n, "precio": p, "var": v, "decimales": d, "ejemplo": True} for s, n, p, v, d in _EJEMPLO]


# TITULO ACTIVOS

def activos() -> list[dict]:
    """Cotizaciones para la sección «Mercados»: las de la fuente real si está conectada y responde, y si no las de ejemplo."""
    try:
        vivas = _cotizaciones_en_vivo()
    except Exception:   # noqa: BLE001 - la portada nunca debe caerse por la fuente de precios
        vivas = None
    return vivas or _ejemplo()


# TITULO NOTICIAS

def noticias(cantidad: int = 6) -> list[dict]:
    """Últimos titulares en español para la portada (si no hay, en cualquier idioma). Devuelve lista vacía si aún no se cargaron.

    Inicia la lectura de las fuentes en segundo plano (una sola vez por proceso) y solo consulta lo que ya está cargado, así que no hace esperar la página. Cada elemento trae `title`, `link`, `fuente`, `fecha` y `desc`."""
    try:
        from componentes_plataforma.noticias import rss
        rss.precargar()
        if not rss.hay_datos():
            return []
        lista = rss.cargar_noticias()
    except Exception:   # noqa: BLE001 - sin red o con una fuente caída, la portada sigue funcionando
        return []
    espanol = [n for n in lista if n.get("idioma") == "ES"]
    return (espanol or lista)[:cantidad]


# -------------------------------------------------------------------------------------------------------
# -------------------------------------- FIN Piña y Jara datos .PY --------------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
