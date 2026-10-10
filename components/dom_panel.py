"""
dom_panel.py
------------
Panel de PROFUNDIDAD DE MERCADO (DOM / Depth of Market), estilo XM: escalera con
el volumen en cola a cada precio (Ask arriba, Bid abajo) alrededor del spread.

Se abre desde el rail de iconos de la derecha (panel_rail.py).

ESTADO: la escalera se centra en el Bid/Ask EN VIVO del activo (precios reales que
se mueven con el mercado), con VOLÚMENES DE MUESTRA. La profundidad real del libro
(`mt5.market_book_add/get`) se conectará después en el motor de `servidor_datos.py`
y se emitirá por el feed; en Forex/CFD (XM) el libro suele venir vacío, por eso de
momento los volúmenes son demostrativos. Un clic en un nivel (pendiente) cargará
ese precio en el ticket.
"""
import streamlit as st
import MetaTrader5 as mt5  # type: ignore[import-untyped]

from tools.mt5_bridge import (MT5_LOCK, inicializar_mt5, obtener_precio_actual,
                              resolver_simbolo, obtener_dom)
from components.live_feed import intervalo

# Volúmenes de muestra por nivel (del más lejano al spread, al más cercano).
# La liquidez suele crecer al alejarse del precio → barras mayores arriba/abajo.
_VOL_ASK = [22, 16, 12, 9, 6]   # arriba (lejos) → abajo (mejor ask, pegado al spread)
_VOL_BID = [6, 9, 13, 18, 25]   # arriba (mejor bid) → abajo (lejos)
_MAXVOL = max(_VOL_ASK + _VOL_BID)

_CSS = """
<style>
  .st-key-dom_panel { background:#0f1620; border:1px solid #202a37; border-radius:14px;
      padding:14px 12px; }
  .dom-h { color:#e6edf3; font-weight:800; font-size:16px; margin:0 0 2px; }
  .dom-sub { color:#8b949e; font-size:12px; margin:0 0 10px; }
  .dom-cols { display:flex; justify-content:space-between; color:#8b949e; font-size:11px;
      padding:0 2px 5px; }
  .dom-row { display:flex; align-items:center; gap:7px; margin-bottom:3px; }
  .dom-bar { flex:1; height:19px; border-radius:3px; position:relative; }
  .dom-bar.ask { background:#1b1420; }
  .dom-bar.bid { background:#111d17; }
  .dom-bar > div { position:absolute; right:0; top:0; height:19px; border-radius:3px; opacity:.6; }
  .dom-bar.ask > div { background:#da3633; }
  .dom-bar.bid > div { background:#2ea043; }
  .dom-bar span { position:absolute; left:6px; top:2px; font-size:11px; color:#e6edf3;
      font-family:ui-monospace,Consolas,monospace; }
  .dom-px { font-size:11.5px; font-family:ui-monospace,Consolas,monospace; min-width:60px;
      text-align:right; font-weight:600; }
  .dom-px.ask { color:#f85149; } .dom-px.bid { color:#3fb950; }
  .dom-spread { display:flex; align-items:center; justify-content:space-between;
      background:#151c27; border:1px solid #2b3546; border-radius:6px; padding:4px 7px; margin:5px 0; }
  .dom-spread .k { font-size:11px; color:#8b949e; }
  .dom-spread .v { font-size:11.5px; color:#e6edf3; font-family:ui-monospace,Consolas,monospace; }
  .dom-nota { color:#8b949e; font-size:10.5px; margin-top:9px; padding-top:8px;
      border-top:1px solid #202a37; line-height:1.4; }
</style>
"""


def renderizar_panel_dom():
    st.html(_CSS)
    with st.container(key="dom_panel"):
        activo = st.session_state.get("activo_seleccionado", "EURUSD...")
        real = resolver_simbolo(activo)
        visible = activo.replace("...", "").strip()
        st.html(f"<div class='dom-h'>Profundidad · {visible}</div>"
                f"<div class='dom-sub'>Libro de órdenes (DOM)</div>")

        @st.fragment(run_every=intervalo("2s"))
        def _escalera():
            inicializar_mt5()
            t = obtener_precio_actual(real)
            if "error" in t or not (t.get("bid") or t.get("ask")):
                st.caption("Sin precio en vivo. ¿Está abierto MetaTrader 5?")
                return
            bid, ask = float(t.get("bid", 0)), float(t.get("ask", 0))
            try:
                with MT5_LOCK:
                    info = mt5.symbol_info(real)
            except Exception:
                info = None
            dig = int(getattr(info, "digits", 5) or 5) if info else 5
            point = (float(getattr(info, "point", 0.0) or 0.0) if info else 0.0) or (10 ** -dig)

            dom = obtener_dom(real, 8)
            if dom.get("disponible"):
                # --- PROFUNDIDAD REAL del bróker ---
                asks = list(reversed(dom["ask"]))      # mayor precio arriba
                bids = dom["bid"]                      # mejor bid arriba
                vols = [e["volume"] for e in asks + bids] or [1]
                mx = max(vols)
                filas = ""
                for e in asks:
                    w = int(e["volume"] / mx * 100)
                    filas += (f"<div class='dom-row'><div class='dom-bar ask'>"
                              f"<div style='width:{w}%'></div><span>{e['volume']:g}</span></div>"
                              f"<div class='dom-px ask'>{e['price']:,.{dig}f}</div></div>")
                filas += (f"<div class='dom-spread'><span class='k'>spread</span>"
                          f"<span class='v'>{round(ask - bid, dig):,.{dig}f}</span></div>")
                for e in bids:
                    w = int(e["volume"] / mx * 100)
                    filas += (f"<div class='dom-row'><div class='dom-bar bid'>"
                              f"<div style='width:{w}%'></div><span>{e['volume']:g}</span></div>"
                              f"<div class='dom-px bid'>{e['price']:,.{dig}f}</div></div>")
                nota = "<div class='dom-nota'>Profundidad real del bróker (libro de órdenes).</div>"
            else:
                # --- Sin profundidad del bróker: escalera DEMO sobre el precio en vivo ---
                paso = round(max(ask - bid, point * 5), dig) or point
                filas = ""
                for i, vol in enumerate(_VOL_ASK):
                    nivel = len(_VOL_ASK) - 1 - i
                    px = round(ask + nivel * paso, dig)
                    w = int(vol / _MAXVOL * 100)
                    filas += (f"<div class='dom-row'><div class='dom-bar ask'>"
                              f"<div style='width:{w}%'></div><span>{vol}</span></div>"
                              f"<div class='dom-px ask'>{px:,.{dig}f}</div></div>")
                filas += (f"<div class='dom-spread'><span class='k'>spread</span>"
                          f"<span class='v'>{round(ask - bid, dig):,.{dig}f}</span></div>")
                for i, vol in enumerate(_VOL_BID):
                    px = round(bid - i * paso, dig)
                    w = int(vol / _MAXVOL * 100)
                    filas += (f"<div class='dom-row'><div class='dom-bar bid'>"
                              f"<div style='width:{w}%'></div><span>{vol}</span></div>"
                              f"<div class='dom-px bid'>{px:,.{dig}f}</div></div>")
                nota = ("<div class='dom-nota'><b>Vista demostrativa.</b> Precios Bid/Ask reales "
                        "en vivo; volúmenes de muestra (XM no entrega profundidad de mercado).</div>")

            st.html(
                "<div class='dom-cols'><span>Volumen</span><span>Precio</span></div>"
                + filas + nota
            )

        _escalera()
