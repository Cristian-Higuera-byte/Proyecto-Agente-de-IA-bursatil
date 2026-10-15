"""
componentes_plataforma/flujo_precios
---------------
Feed de precios EN VIVO del navegador (streaming por SSE desde servidor_datos.py).

Cómo funciona:
  - Los componentes marcan sus números con atributos `data-pj-*`
    (p. ej. <span data-pj-s="EURUSD..." data-pj-f="px">1.12010</span>).
  - `inyectar_feed()` mete un iframe invisible con un script que:
      1) junta todos los símbolos marcados en la página,
      2) abre UNA conexión SSE a `/stream?s=...` del servidor de datos,
      3) en cada tick reescribe SOLO el texto/color de esos elementos en el DOM
         (sin reejecutar Streamlit → sin parpadeo ni colisiones de deltas),
      4) reenvía el tick por BroadcastChannel('pj-ticks') para que el gráfico
         mueva la vela actual al instante.
  - Si Streamlit redibuja un bloque (rerun de un fragmento), un MutationObserver
    repinta enseguida con el último tick conocido.

Atributos soportados:
  data-pj-s     símbolo tal como se pide al servidor (con o sin '...')
  data-pj-f     campo: px | bid | ask | side | var | ch | pct | spr
  data-pj-d     decimales (por defecto: 2 si el precio > 100, si no 5)
  data-pj-pre   prefijo (p. ej. "$")
  data-pj-side  BUY | SELL  (para data-pj-f="side": ask o bid)
  data-pj-pip   tamaño del pip (para data-pj-f="spr")
  data-pj-flash "1" → colorea verde/rojo según suba/baje el último tick
  data-pj-up / data-pj-dn  colores de variación positiva/negativa
  data-pj-acc   equity | profit   (datos de la cuenta, sin data-pj-s)
                con data-pj-suf (sufijo) y data-pj-zero="1" (mostrar +0.00 en vez de vacío)
  data-pj-pos   ticket de una posición → su P/G neto (profit + swap)
  data-pj-posc  ticket de una posición → su precio actual (data-pj-d decimales)
  data-pj-acc + data-pj-fmt  cualquier dato de la cuenta (balance, margin,
                margin_free, margin_level, credit, equity, profit) con formato
                usd ("$1,234.56") | pct ("565.65%") | signed ("+12.30" + data-pj-suf);
                data-pj-color="1" lo pinta verde/rojo según el signo
  data-pj-bar   campo de la cuenta (0-100) → ancho de una barra (style.width en %)
  data-pj-spark símbolo de un mini-gráfico (<img> dentro); data-pj-vals = semilla
                "v1,v2,..." → se redibuja en el navegador con cada tick

Si el servidor de datos NO está corriendo, no se inyecta nada y los fragmentos
`run_every` siguen refrescando como antes (intervalo rápido).
"""
from componentes_plataforma.flujo_precios.atributos import attrs
from componentes_plataforma.flujo_precios.inyeccion import inyectar_feed
from componentes_plataforma.flujo_precios.servidor import API_URL, feed_activo, intervalo

__all__ = ["API_URL", "feed_activo", "intervalo", "attrs", "inyectar_feed"]
