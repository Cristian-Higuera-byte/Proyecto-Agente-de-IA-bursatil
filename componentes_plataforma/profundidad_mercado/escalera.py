"""HTML de la escalera del DOM: filas Ask (arriba) y Bid (abajo) alrededor del spread."""
from __future__ import annotations

# Volúmenes de muestra por nivel (del más lejano al spread, al más cercano).
# La liquidez suele crecer al alejarse del precio → barras mayores arriba/abajo.
VOL_ASK = [22, 16, 12, 9, 6]   # arriba (lejos) → abajo (mejor ask, pegado al spread)
VOL_BID = [6, 9, 13, 18, 25]   # arriba (mejor bid) → abajo (lejos)
MAXVOL = max(VOL_ASK + VOL_BID)


def _fila(lado: str, volumen_txt: str, precio_txt: str, ancho: int) -> str:
    """Una fila de la escalera. lado = 'ask' | 'bid'."""
    return (f"<div class='dom-row'><div class='dom-bar {lado}'>"
            f"<div style='width:{ancho}%'></div><span>{volumen_txt}</span></div>"
            f"<div class='dom-px {lado}'>{precio_txt}</div></div>")


def _spread(ask: float, bid: float, dig: int) -> str:
    return (f"<div class='dom-spread'><span class='k'>spread</span>"
            f"<span class='v'>{round(ask - bid, dig):,.{dig}f}</span></div>")


def filas_reales(dom: dict, bid: float, ask: float, dig: int) -> tuple[str, str]:
    """Escalera con la PROFUNDIDAD REAL del bróker. Devuelve (filas, nota)."""
    asks = list(reversed(dom["ask"]))      # mayor precio arriba
    bids = dom["bid"]                      # mejor bid arriba
    vols = [e["volume"] for e in asks + bids] or [1]
    mx = max(vols)
    filas = ""
    for e in asks:
        filas += _fila("ask", f"{e['volume']:g}", f"{e['price']:,.{dig}f}", int(e["volume"] / mx * 100))
    filas += _spread(ask, bid, dig)
    for e in bids:
        filas += _fila("bid", f"{e['volume']:g}", f"{e['price']:,.{dig}f}", int(e["volume"] / mx * 100))
    nota = "<div class='dom-nota'>Profundidad real del bróker (libro de órdenes).</div>"
    return filas, nota


def filas_demo(bid: float, ask: float, dig: int, point: float) -> tuple[str, str]:
    """Sin profundidad del bróker: escalera DEMO sobre el precio en vivo. Devuelve (filas, nota)."""
    paso = round(max(ask - bid, point * 5), dig) or point
    filas = ""
    for i, vol in enumerate(VOL_ASK):
        nivel = len(VOL_ASK) - 1 - i
        px = round(ask + nivel * paso, dig)
        filas += _fila("ask", str(vol), f"{px:,.{dig}f}", int(vol / MAXVOL * 100))
    filas += _spread(ask, bid, dig)
    for i, vol in enumerate(VOL_BID):
        px = round(bid - i * paso, dig)
        filas += _fila("bid", str(vol), f"{px:,.{dig}f}", int(vol / MAXVOL * 100))
    nota = ("<div class='dom-nota'><b>Vista demostrativa.</b> Precios Bid/Ask reales "
            "en vivo; volúmenes de muestra (XM no entrega profundidad de mercado).</div>")
    return filas, nota


def html_escalera(filas: str, nota: str) -> str:
    return "<div class='dom-cols'><span>Volumen</span><span>Precio</span></div>" + filas + nota
