"""
mercados_panel.py
-----------------
Página "Mercados" (barra lateral), con diseño de plataforma de bróker:
- Resumen del mercado: 5 referencias (S&P 500, Nasdaq, Oro, EUR/USD, Bitcoin)
  con precio y variación del día en vivo + tendencia de las últimas 24 h.
- Pestañas por categoría (con cantidad), buscador y orden.
- Tabla: instrumento, precio, cambio, cambio %, rango del día (barra),
  tendencia de 5 días (mini-gráfico) y estado del mercado (abierto/cerrado).
- Cada fila / tarjeta es CLICABLE -> ficha del instrumento (modal): precio en
  vivo, caja Vender/Comprar con spread, gráfico interactivo (Lightweight Charts)
  con periodos 1S/1M/3M/6M/1A, rendimiento, estadísticas clave y
  especificaciones del contrato.

Precios, cambios y Bid/Ask se pintan en vivo con el feed SSE (live_feed.py);
sin servidor de datos, los fragmentos se refrescan cada pocos segundos.
La variación es la DEL DÍA (contra el cierre diario anterior), la misma base
que usan Favoritos, la lista de activos y el feed.

Los nombres cambian entre brókers (XM: US30Cash, GOLD, SpainCash, futuros
"COCOA-DEC26", acciones por nombre de empresa "Apple"...). `_resolver()` prueba
los candidatos del catálogo, luego el sufijo Cash, el futuro vigente y, para
acciones, el ticker que MT5 trae en la descripción ("Apple Inc (AAPL.OQ)").
"""
import base64
import json
import re
import time
from datetime import datetime, timezone

import streamlit as st
import streamlit.components.v1 as components
import MetaTrader5 as mt5  # type: ignore[import-untyped]

from tools.mt5_bridge import (
    MT5_LOCK, inicializar_mt5, resolver_simbolo, obtener_datos_historicos,
)
from components.iconos import icono_activo   # íconos estilo XM (comunes)
from components.live_feed import attrs as _live, intervalo
from components.market_data import _cierre_previo, _historial_sparkline

# (candidatos, nombre). El primer candidato que exista en el bróker se usa.
_CATALOGO = {
    "Índices": [
        (("US30",), "Dow Jones"), (("US500",), "S&P 500"), (("NAS100",), "Nasdaq 100"),
        (("US2000",), "Russell 2000"), (("VIX",), "Volatilidad VIX"),
        (("DXY", "USDX"), "Índice Dólar"), (("GER40",), "DAX 40"),
        (("UK100",), "FTSE 100"), (("FRA40",), "CAC 40"), (("ESP35", "Spain"), "IBEX 35"),
        (("EU50",), "Euro Stoxx 50"), (("ITA40", "IT40"), "FTSE MIB"),
        (("NETH25",), "AEX 25"), (("SWI20",), "SMI 20"), (("JP225",), "Nikkei 225"),
        (("AUS200",), "ASX 200"), (("HK50",), "Hang Seng"), (("CHINA50", "CHN50"), "China A50"),
    ],
    "Divisas": [
        (("EURUSD",), "Euro / Dólar"), (("GBPUSD",), "Libra / Dólar"),
        (("USDJPY",), "Dólar / Yen"), (("USDCHF",), "Dólar / Franco suizo"),
        (("AUDUSD",), "Dólar aus. / Dólar"), (("USDCAD",), "Dólar / Dólar can."),
        (("NZDUSD",), "Dólar NZ / Dólar"), (("EURJPY",), "Euro / Yen"),
        (("EURGBP",), "Euro / Libra"), (("GBPJPY",), "Libra / Yen"),
        (("EURCHF",), "Euro / Franco suizo"), (("EURAUD",), "Euro / Dólar aus."),
        (("AUDJPY",), "Dólar aus. / Yen"), (("CADJPY",), "Dólar can. / Yen"),
        (("CHFJPY",), "Franco suizo / Yen"), (("NZDJPY",), "Dólar NZ / Yen"),
        (("GBPAUD",), "Libra / Dólar aus."), (("USDMXN",), "Dólar / Peso mexicano"),
        (("USDZAR",), "Dólar / Rand"), (("USDSGD",), "Dólar / Dólar sing."),
    ],
    "Materias primas": [
        (("XAUUSD",), "Oro"), (("XAGUSD",), "Plata"), (("XPTUSD",), "Platino"),
        (("XPDUSD",), "Paladio"), (("XCUUSD", "HGCOP"), "Cobre"),
        (("USOIL",), "Petróleo WTI"), (("UKOIL",), "Petróleo Brent"),
        (("NGAS",), "Gas natural"), (("COFFEE", "COFFE"), "Café"), (("COCOA",), "Cacao"),
        (("SUGAR",), "Azúcar"), (("WHEAT",), "Trigo"), (("CORN",), "Maíz"),
        (("SOYBEAN", "SBEAN"), "Soja"), (("COTTON", "COTTO"), "Algodón"),
    ],
    "Criptomonedas": [
        (("BTCUSD",), "Bitcoin"), (("ETHUSD",), "Ethereum"), (("XRPUSD",), "XRP"),
        (("SOLUSD",), "Solana"), (("DOGEUSD", "DOGUSD"), "Dogecoin"),
        (("ADAUSD",), "Cardano"), (("LTCUSD",), "Litecoin"), (("BNBUSD",), "BNB"),
        (("AVAXUSD",), "Avalanche"), (("LINKUSD",), "Chainlink"), (("DOTUSD",), "Polkadot"),
        (("BCHUSD",), "Bitcoin Cash"), (("MATICUSD",), "Polygon"), (("UNIUSD",), "Uniswap"),
        (("ATOMUSD",), "Cosmos"), (("XLMUSD",), "Stellar"), (("SHIBUSD",), "Shiba Inu"),
    ],
    "Acciones": [
        (("AAPL",), "Apple"), (("MSFT",), "Microsoft"), (("NVDA",), "NVIDIA"),
        (("AMZN",), "Amazon"), (("GOOGL", "GOOG"), "Alphabet"), (("META",), "Meta Platforms"),
        (("TSLA",), "Tesla"), (("NFLX",), "Netflix"), (("AMD",), "AMD"),
        (("JPM",), "JPMorgan Chase"), (("V",), "Visa"), (("WMT",), "Walmart"),
        (("KO",), "Coca-Cola"), (("DIS",), "Disney"), (("BABA",), "Alibaba"),
        (("INTC",), "Intel"), (("BA",), "Boeing"), (("ORCL",), "Oracle"),
        (("CSCO",), "Cisco"), (("PFE",), "Pfizer"),
    ],
}

# "Pulso del mercado": la referencia más seguida de cada mercado
# (categoría, índice dentro del catálogo, qué representa)
_RESUMEN = [("Índices", 1, "Bolsa EE. UU."), ("Índices", 2, "Tecnología"),
            ("Materias primas", 0, "Refugio"), ("Divisas", 0, "Divisa más operada"),
            ("Criptomonedas", 0, "Cripto")]

_ORDENES = ["Predeterminado", "Mayor alza", "Mayor baja", "Nombre (A-Z)"]

# Columnas de la tabla — cabecera y filas comparten el reparto
_GRID = "minmax(230px,2.3fr) 1.15fr 0.95fr 0.95fr 1.55fr 112px 96px"

_VERDE, _ROJO, _GRIS = "#3fb950", "#f85149", "#8b949e"

# OJO: nada con forma de etiqueta HTML dentro de este CSS (ni en comentarios):
# el saneador de st.html descartaría el bloque completo.
_CSS = f"""
<style>
  .mkt-hdr {{ display:flex; align-items:flex-end; justify-content:space-between; margin:2px 0 14px; }}
  .mkt-title {{ color:#e6edf3; font-size:24px; font-weight:800; margin:0; letter-spacing:-.2px; }}
  .mkt-sub {{ color:{_GRIS}; font-size:13px; margin-top:3px; }}
  .mkt-live {{ display:inline-flex; align-items:center; gap:7px; color:#c9d1d9; font-size:12px;
               background:#0f1620; border:1px solid #202a37; border-radius:999px; padding:5px 12px; }}
  .mkt-dot {{ width:7px; height:7px; border-radius:50%; background:{_VERDE};
              box-shadow:0 0 0 3px rgba(63,185,80,.18); display:inline-block; }}
  .mkt-dot.off {{ background:#6e7681; box-shadow:none; }}

  /* Resumen del mercado */
  .mkt-card {{ background:#0f1620; border:1px solid #202a37; border-radius:12px;
               padding:12px 14px 10px; transition:border-color .15s, background .15s; }}
  .mkt-card-top {{ display:flex; align-items:center; gap:9px; }}
  .mkt-card-nm {{ color:#e6edf3; font-size:13px; font-weight:700; line-height:1.15; }}
  .mkt-card-sym {{ color:{_GRIS}; font-size:11px; }}
  .mkt-card-px {{ color:#e6edf3; font-size:20px; font-weight:700; margin-top:10px;
                  font-family:ui-monospace,Consolas,monospace; font-variant-numeric:tabular-nums; }}
  .mkt-card-bot {{ display:flex; align-items:flex-end; justify-content:space-between; margin-top:4px; }}
  .mkt-card-bot img, .mkt-card-bot svg {{ display:block; }}
  .mkt-card-tag {{ margin-left:auto; align-self:flex-start; color:#c9d1d9; font-size:10.5px;
                   background:#161b22; border:1px solid #30363d; border-radius:999px; padding:1px 8px;
                   white-space:nowrap; }}
  .mkt-sec {{ display:flex; align-items:baseline; gap:10px; margin:0 0 10px; }}
  .mkt-sec b {{ color:#e6edf3; font-size:15px; }}
  .mkt-sec span {{ color:{_GRIS}; font-size:12px; }}
  [class*="st-key-mktcard_"] {{ position:relative; }}
  [class*="st-key-mktcard_"]:hover .mkt-card {{ border-color:#30363d; background:#121b27; }}

  /* Pestañas de categoría (segmentado de Streamlit con forma de pestañas) */
  .st-key-mkt_tabs [role="radiogroup"] {{ gap:4px; border-bottom:1px solid #202a37; width:100%;
                                         flex-wrap:wrap; }}
  .st-key-mkt_tabs [role="radiogroup"] button {{ background:transparent !important; border:none !important;
      border-radius:0 !important; border-bottom:2px solid transparent !important; color:{_GRIS} !important;
      padding:8px 14px !important; margin-bottom:-1px; box-shadow:none !important; }}
  .st-key-mkt_tabs [role="radiogroup"] button:hover {{ color:#e6edf3 !important; }}
  .st-key-mkt_tabs [role="radiogroup"] button[aria-checked="true"] {{
      color:#e6edf3 !important; border-bottom-color:#ff8f00 !important; font-weight:700; }}
  .st-key-mkt_tabs [role="radiogroup"] button p {{ font-size:14px; }}

  /* Tabla */
  .mkt-tabla-wrap {{ background:#0d1117; border:1px solid #202a37; border-radius:12px; overflow:hidden; }}
  .mkt-head, .mkt-row {{ display:grid; grid-template-columns:{_GRID}; align-items:center; }}
  .mkt-head > div, .mkt-row > div {{ padding:0 14px; }}
  .mkt-head {{ background:#0f1620; border-bottom:1px solid #202a37; color:{_GRIS}; font-size:11px;
               font-weight:600; text-transform:uppercase; letter-spacing:.5px; height:38px; }}
  .mkt-row {{ border-bottom:1px solid #161d27; font-size:14px; color:#e6edf3; height:60px; }}
  .mkt-r {{ text-align:right; justify-content:flex-end; }}
  .mkt-num {{ font-family:ui-monospace,Consolas,monospace; font-variant-numeric:tabular-nums; }}
  .mkt-nm {{ display:flex; align-items:center; gap:11px; min-width:0; }}
  .mkt-nm b {{ font-size:14px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .mkt-nm small {{ display:block; color:{_GRIS}; font-size:11px; font-weight:400; margin-top:1px; }}
  .mkt-ic {{ display:inline-flex; align-items:center; flex:0 0 auto; }}
  .mkt-pill {{ display:inline-block; min-width:78px; text-align:center; border-radius:6px;
               padding:3px 8px; font-size:12.5px; font-weight:700; }}
  .mkt-rng {{ display:flex; align-items:center; gap:8px; font-size:11px; color:{_GRIS}; }}
  .mkt-rng .bar {{ position:relative; flex:1; height:4px; border-radius:3px;
                   background:linear-gradient(90deg, rgba(248,81,73,.55), #30363d 50%, rgba(63,185,80,.55)); }}
  .mkt-rng .dot {{ position:absolute; top:-3px; width:10px; height:10px; border-radius:50%;
                   background:#e6edf3; border:2px solid #0d1117; transform:translateX(-50%); }}
  .mkt-est {{ display:inline-flex; align-items:center; gap:6px; font-size:12px; color:#c9d1d9; }}
  .mkt-chev {{ color:#6e7681; font-size:18px; margin-left:6px; }}
  .mkt-vacio {{ color:{_GRIS}; padding:28px 16px; text-align:center; font-size:13px; }}
  .mkt-pie {{ color:{_GRIS}; font-size:12px; margin-top:10px; }}
  .st-key-mkt_loadjs {{ position:absolute !important; width:0 !important; height:0 !important;
                        overflow:hidden !important; }}
  .mkt-nota {{ display:flex; align-items:center; gap:8px; color:{_GRIS}; font-size:12.5px; margin:0 0 10px 2px; }}
  .mkt-nota b {{ color:#e6edf3; font-weight:600; }}
  .mkt-nota .ico {{ font-family:'Material Symbols Rounded'; font-size:17px; color:#ff8f00; }}

  /* Filas y tarjetas clicables: botón invisible que cubre todo (patrón watchlist) */
  .st-key-mkt_tabla {{ background:#0d1117; border:1px solid #202a37;
                       border-radius:12px; overflow:hidden; }}
  .st-key-mkt_tabla [data-testid="stVerticalBlock"] {{ gap:0 !important; }}
  .st-key-mkt_tabla [class*="st-key-mktrow_"]:last-child .mkt-row {{ border-bottom:none; }}
  [class*="st-key-mktrow_"] {{ position:relative; }}
  [class*="st-key-mktrow_"]:hover .mkt-row {{ background:#111925; }}
  [class*="st-key-mktclk_"], [class*="st-key-ficov_"] {{
      position:absolute !important; top:0 !important; right:0 !important; bottom:0 !important;
      left:0 !important; width:100% !important; height:100% !important;
      margin:0 !important; padding:0 !important; z-index:2;
  }}
  [class*="st-key-mktclk_"] *, [class*="st-key-ficov_"] * {{
      width:100% !important; height:100% !important; min-height:0 !important;
      margin:0 !important; padding:0 !important;
  }}
  [class*="st-key-mktclk_"] button, [class*="st-key-ficov_"] button {{ opacity:0; cursor:pointer; }}

  /* ---------------- Ficha (modal) ---------------- */
  [data-testid="stDialog"]:has(.st-key-fic_root) section {{
      background:#0d1117 !important; border:1px solid #30363d; border-radius:16px; }}
  .fic-head {{ display:flex; align-items:center; gap:14px; }}
  .fic-nm {{ font-size:22px; font-weight:800; color:#e6edf3; line-height:1.1; }}
  .fic-chips {{ display:flex; flex-wrap:wrap; gap:6px; margin-top:6px; align-items:center; }}
  .fic-chip {{ display:inline-flex; align-items:center; gap:6px; background:#161b22; border:1px solid #30363d;
               color:#c9d1d9; font-size:11.5px; padding:2px 9px; border-radius:999px; }}
  .fic-px {{ font-size:38px; font-weight:800; line-height:1; color:#e6edf3;
             font-family:ui-monospace,Consolas,monospace; font-variant-numeric:tabular-nums; }}
  .fic-pxrow {{ display:flex; align-items:center; gap:12px; flex-wrap:wrap; margin-top:14px; }}
  .fic-pxsub {{ color:{_GRIS}; font-size:12px; margin-top:8px; }}
  .fic-trade {{ display:grid; grid-template-columns:1fr auto 1fr; align-items:stretch; gap:0; }}
  .fic-side {{ border-radius:10px; padding:10px 14px; color:#fff; }}
  .fic-side .k {{ font-size:11px; font-weight:700; letter-spacing:.6px; opacity:.9; }}
  .fic-side .v {{ font-size:19px; font-weight:800; margin-top:2px;
                  font-family:ui-monospace,Consolas,monospace; font-variant-numeric:tabular-nums; }}
  .fic-sell {{ background:linear-gradient(135deg,#f85149,#da3633); }}
  .fic-buy {{ background:linear-gradient(135deg,#3fb950,#2ea043); text-align:right; }}
  .fic-spr {{ align-self:center; margin:0 -10px; z-index:1; background:#0d1117; border:1px solid #30363d;
              border-radius:8px; padding:4px 8px; text-align:center; min-width:62px; }}
  .fic-spr .k {{ color:{_GRIS}; font-size:10px; }}
  .fic-spr .v {{ color:#e6edf3; font-size:13px; font-weight:700; font-family:ui-monospace,Consolas,monospace; }}
  [class*="st-key-ficsd_"] {{ position:relative; }}
  [class*="st-key-ficsd_"]:hover .fic-side {{ filter:brightness(1.08); }}
  .fic-perf {{ display:grid; grid-template-columns:repeat(6,1fr); gap:8px; }}
  .fic-perf > div {{ background:#0f1620; border:1px solid #202a37; border-radius:10px; padding:9px 10px; }}
  .fic-perf .k {{ color:{_GRIS}; font-size:11px; }}
  .fic-perf .v {{ font-weight:700; font-size:15px; margin-top:2px; font-family:ui-monospace,Consolas,monospace; }}
  .fic-perf .b {{ height:3px; border-radius:2px; margin-top:7px; background:#202a37; position:relative; overflow:hidden; }}
  .fic-perf .b span {{ position:absolute; top:0; bottom:0; }}
  .fic-box {{ background:#0f1620; border:1px solid #202a37; border-radius:12px; padding:14px 16px; height:100%; }}
  .fic-box h4 {{ color:#e6edf3; font-size:13px; font-weight:700; margin:0 0 8px; text-transform:uppercase;
                 letter-spacing:.5px; }}
  .fic-r {{ display:flex; justify-content:space-between; gap:12px; padding:7px 0;
            border-bottom:1px solid #161d27; font-size:13px; }}
  .fic-r:last-child {{ border-bottom:none; }}
  .fic-r .k {{ color:{_GRIS}; }}
  .fic-r .v {{ color:#e6edf3; font-family:ui-monospace,Consolas,monospace; text-align:right; }}
  .fic-rng {{ padding:8px 0 10px; border-bottom:1px solid #161d27; }}
  .fic-rng .t {{ display:flex; justify-content:space-between; color:{_GRIS}; font-size:12px; }}
  .fic-rng .bar {{ position:relative; height:5px; border-radius:3px; margin:8px 0 6px;
                   background:linear-gradient(90deg, rgba(248,81,73,.6), #30363d 50%, rgba(63,185,80,.6)); }}
  .fic-rng .dot {{ position:absolute; top:-4px; width:13px; height:13px; border-radius:50%;
                   background:#e6edf3; border:2px solid #0f1620; transform:translateX(-50%); }}
  .fic-rng .n {{ display:flex; justify-content:space-between; color:#c9d1d9; font-size:12px;
                 font-family:ui-monospace,Consolas,monospace; }}
  .st-key-fic_operar button {{ background:linear-gradient(90deg,#ff4b4b,#ff8f00) !important;
      border:none !important; color:#fff !important; font-weight:700; }}
  .st-key-fic_operar button:hover {{ filter:brightness(1.08); }}
</style>
"""


# ----------------------------- Datos -----------------------------
def _g(info, attr):
    return getattr(info, attr, 0) or 0


class _SinDatos(Exception):
    """MT5 no entregó datos: se lanza para que st.cache_data NO cachee el vacío."""


@st.cache_data(ttl=600, show_spinner=False)
def _indice_broker_cache():
    with MT5_LOCK:
        simbolos = mt5.symbols_get() or []
    if not simbolos:
        raise _SinDatos("symbols_get")
    nombres = {s.name for s in simbolos}
    por_ticker = {}
    for s in simbolos:
        # "Apple Inc (AAPL.OQ)" -> AAPL ; se ignoran las variantes _turbo
        m = re.search(r"\(([A-Za-z0-9\-]+)(?:\.[A-Za-z]+)?\)\s*$", s.description or "")
        if m and "_turbo" not in s.name:
            por_ticker.setdefault(m.group(1).upper(), s.name)
    return nombres, por_ticker


def _indice_broker():
    try:
        return _indice_broker_cache()
    except Exception:
        return set(), {}


def _resolver(candidatos) -> str | None:
    """Nombre real en el bróker del primer candidato que exista, o None."""
    nombres, por_ticker = _indice_broker()
    if not nombres:
        return None
    for c in candidatos:
        r = resolver_simbolo(c)
        if r in nombres:
            return r
        if c + "Cash" in nombres:                         # XM: FRA40Cash, SpainCash...
            return c + "Cash"
        futuros = sorted(n for n in nombres if n.upper().startswith(c.upper() + "-"))
        if futuros:                                       # XM: COCOA-DEC26
            return futuros[0]
    for c in candidatos:                                  # acciones: ticker en la descripción
        if c.upper() in por_ticker:
            return por_ticker[c.upper()]
    return None


@st.cache_data(ttl=600, show_spinner=False)
def _items_cache(categoria: str):
    out = []
    for i, (cands, nombre) in enumerate(_CATALOGO.get(categoria, [])):
        real = _resolver(cands)
        if real:
            out.append((real, nombre, i))
    if not out:
        raise _SinDatos(categoria)        # MT5 sin conexión: no cachear el vacío
    return out


def _items(categoria: str):
    """[(real, nombre, índice)] de la categoría, solo los que existen en el bróker."""
    try:
        return _items_cache(categoria)
    except Exception:
        return []


@st.cache_data(ttl=10, show_spinner=False)
def _hora_servidor() -> int:
    """Hora del servidor del bróker (unix) ≈ último tick de las cripto (cotizan 24/7)."""
    mejor = 0
    for c in ("BTCUSD", "ETHUSD", "EURUSD"):
        try:
            with MT5_LOCK:
                t = mt5.symbol_info_tick(resolver_simbolo(c))
            mejor = max(mejor, int(getattr(t, "time", 0) or 0))
        except Exception:
            pass
    return mejor


def _abierto(t_tick: int) -> bool:
    ref = _hora_servidor()
    return bool(t_tick and ref and ref - t_tick < 180)


@st.cache_data(ttl=300, show_spinner=False)
def _serie_cache(real: str, tf: int, n: int):
    df = obtener_datos_historicos(real, timeframe=tf, n_velas=n)
    if df is None or df.empty:
        raise _SinDatos(real)
    return df


def _serie(real: str, tf: int, n: int):
    try:
        return _serie_cache(real, tf, n)
    except Exception:
        return None


def _svg_spark(vals, w=104, h=34, area=True) -> str:
    """Mini-gráfico como <img> data-URI (st.html sanea el SVG en línea)."""
    if not vals or len(vals) < 2:
        return f"<span style='display:inline-block;width:{w}px;height:{h}px;'></span>"
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    n = len(vals)
    pts = [(i * w / (n - 1), h - 3 - (v - lo) / rng * (h - 6)) for i, v in enumerate(vals)]
    col = _VERDE if vals[-1] >= vals[0] else _ROJO
    linea = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    relleno = ""
    if area:
        relleno = (f"<defs><linearGradient id='g' x1='0' y1='0' x2='0' y2='1'>"
                   f"<stop offset='0' stop-color='{col}' stop-opacity='.28'/>"
                   f"<stop offset='1' stop-color='{col}' stop-opacity='0'/></linearGradient></defs>"
                   f"<polygon fill='url(#g)' points='0,{h} {linea} {w},{h}'/>")
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}' viewBox='0 0 {w} {h}'>"
           f"{relleno}<polyline fill='none' stroke='{col}' stroke-width='1.6' "
           f"stroke-linejoin='round' points='{linea}'/></svg>")
    b64 = base64.b64encode(svg.encode()).decode()
    return f"<img src='data:image/svg+xml;base64,{b64}' width='{w}' height='{h}' alt=''>"


def _fila(real: str, nombre: str):
    """Datos de una fila desde MT5, o None si no hay precio."""
    try:
        with MT5_LOCK:
            mt5.symbol_select(real, True)
            info = mt5.symbol_info(real)
            tick = mt5.symbol_info_tick(real) if info is not None else None
    except Exception:
        return None
    if info is None:
        return None
    last = float(getattr(tick, "bid", 0) or 0) if tick is not None else 0.0
    if last <= 0:
        last = float(_g(info, "bid") or _g(info, "last"))
    if last <= 0:   # bolsa cerrada (acciones antes de la apertura): último cierre diario
        d1 = _serie(real, mt5.TIMEFRAME_D1, 2)
        last = float(d1["close"].iloc[-1]) if d1 is not None else 0.0
    if last <= 0:
        return None
    dig = int(_g(info, "digits") or 2)
    hi = float(_g(info, "bidhigh") or last)
    lo = float(_g(info, "bidlow") or last)
    prev = _cierre_previo(real)
    ch = (last - prev) if prev else 0.0
    pct = (ch / prev * 100) if prev else 0.0
    return {"sym": real, "label": nombre, "last": last, "hi": max(hi, last), "lo": min(lo, last),
            "ch": ch, "pct": pct, "dig": dig, "t": int(getattr(tick, "time", 0) or 0),
            "desc": getattr(info, "description", "") or ""}


def _abrir_ficha(real: str, nombre: str, cat: str):
    st.session_state.mkt_detalle = {"sym": real, "label": nombre, "cat": cat}
    st.rerun()


# ----------------------------- Piezas HTML -----------------------------
def _pill(f) -> str:
    sube = f["ch"] >= 0
    col, bg = (_VERDE, "rgba(63,185,80,.12)") if sube else (_ROJO, "rgba(248,81,73,.12)")
    txt = f"▲ +{f['pct']:.2f}%" if sube else f"▼ {f['pct']:.2f}%"
    return (f"<span class='mkt-pill' style='color:{col};background:{bg};' "
            f"{_live(f['sym'], 'pct', pill=1)}>{txt}</span>")


def _rango_html(f) -> str:
    d = f["dig"]
    pos = 50.0 if f["hi"] <= f["lo"] else (f["last"] - f["lo"]) / (f["hi"] - f["lo"]) * 100
    return (f"<div class='mkt-rng'><span class='mkt-num'>{f['lo']:,.{d}f}</span>"
            f"<div class='bar'><div class='dot' style='left:{max(0, min(100, pos)):.1f}%;'></div></div>"
            f"<span class='mkt-num'>{f['hi']:,.{d}f}</span></div>")


def _fila_html(f) -> str:
    d = f["dig"]
    col = _VERDE if f["ch"] >= 0 else _ROJO
    h1 = _serie(f["sym"], mt5.TIMEFRAME_H1, 120)
    spark = _svg_spark([float(x) for x in h1["close"].tolist()] if h1 is not None else [], 104, 30, area=False)
    abierto = _abierto(f["t"])
    estado = (f"<span class='mkt-est'><span class='mkt-dot{'' if abierto else ' off'}'></span>"
              f"{'Abierto' if abierto else 'Cerrado'}</span>")
    return (
        "<div class='mkt-row'>"
        f"<div><div class='mkt-nm'><span class='mkt-ic'>{icono_activo(f['sym'], 32)}</span>"
        f"<div style='min-width:0;'><b>{f['label']}</b><small>{f['sym']}</small></div></div></div>"
        f"<div class='mkt-r mkt-num' style='font-weight:700;' "
        f"{_live(f['sym'], 'px', d=d, flash=1)}>{f['last']:,.{d}f}</div>"
        f"<div class='mkt-r mkt-num' style='color:{col};' {_live(f['sym'], 'ch', d=d)}>{f['ch']:+,.{d}f}</div>"
        f"<div class='mkt-r'>{_pill(f)}</div>"
        f"<div>{_rango_html(f)}</div>"
        f"<div style='display:flex;justify-content:center;'>{spark}</div>"
        f"<div style='display:flex;align-items:center;justify-content:space-between;'>{estado}"
        "<span class='mkt-chev'>›</span></div>"
        "</div>"
    )


def _tarjeta_html(f, tag: str) -> str:
    d = f["dig"]
    # Mini-gráfico EN VIVO: semilla M1 (últimos 30 min) y el feed agrega cada tick
    vals = _historial_sparkline(f["sym"])
    semilla = ",".join(f"{v:.6g}" for v in vals)
    spark = (f"<span data-pj-spark='{f['sym']}' data-pj-vals='{semilla}'>"
             f"{_svg_spark(vals, 92, 40)}</span>")
    return (
        "<div class='mkt-card'>"
        f"<div class='mkt-card-top'><span class='mkt-ic'>{icono_activo(f['sym'], 28)}</span>"
        f"<div><div class='mkt-card-nm'>{f['label']}</div><div class='mkt-card-sym'>{f['sym']}</div></div>"
        f"<span class='mkt-card-tag'>{tag}</span></div>"
        f"<div class='mkt-card-px' {_live(f['sym'], 'px', d=d, flash=1)}>{f['last']:,.{d}f}</div>"
        f"<div class='mkt-card-bot'>{_pill(f)}{spark}</div>"
        "</div>"
    )


# ----------------------------- Secciones de la página -----------------------------
def _resumen():
    filas = []
    for cat, idx, tag in _RESUMEN:
        cands, nombre = _CATALOGO[cat][idx]
        real = _resolver(cands)
        f = _fila(real, nombre) if real else None
        if f:
            filas.append((f, cat, tag))
    if not filas:
        return
    st.html("<div class='mkt-sec'><b>Pulso del mercado</b><span>la referencia más seguida de "
            "cada mercado · variación de hoy y movimiento de los últimos 30 minutos</span></div>")
    cols = st.columns(len(filas), gap="small")
    for i, (f, cat, tag) in enumerate(filas):
        with cols[i]:
            with st.container(key=f"mktcard_{i}"):
                st.html(_tarjeta_html(f, tag))
                if st.button("ver", key=f"mktclk_card_{f['sym']}"):
                    _abrir_ficha(f["sym"], f["label"], cat)


def _render_tabla(categoria: str):
    filas = [f for f in (_fila(r, n) for r, n, _ in _items(categoria)) if f]
    total = len(filas)

    q = (st.session_state.get("mkt_q") or "").strip().lower()
    if q:
        filas = [f for f in filas if q in f["label"].lower() or q in f["sym"].lower()
                 or q in f["desc"].lower()]
    orden = st.session_state.get("mkt_orden") or _ORDENES[0]
    if orden == "Mayor alza":
        filas.sort(key=lambda f: f["pct"], reverse=True)
    elif orden == "Mayor baja":
        filas.sort(key=lambda f: f["pct"])
    elif orden == "Nombre (A-Z)":
        filas.sort(key=lambda f: f["label"].lower())

    # Cabecera y filas en el MISMO contenedor (gap 0): si la cabecera va aparte,
    # Streamlit agrega su separación de ~1rem entre ambos bloques.
    with st.container(key="mkt_tabla"):
        st.html(
            "<div class='mkt-head'><div>Instrumento</div><div class='mkt-r'>Precio</div>"
            "<div class='mkt-r'>Cambio</div><div class='mkt-r'>Cambio %</div>"
            "<div>Rango del día</div><div style='text-align:center;'>5 días</div><div>Estado</div></div>"
        )
        if not filas:
            msg = ("Ningún instrumento coincide con la búsqueda." if q else
                   "No hay datos para esta categoría. Verifica que MetaTrader 5 esté abierto "
                   "y que el bróker tenga estos instrumentos.")
            st.html(f"<div class='mkt-vacio'>{msg}</div>")
            return total, 0
        for i, f in enumerate(filas):
            with st.container(key=f"mktrow_{i}"):
                st.html(_fila_html(f))
                if st.button("ver", key=f"mktclk_{f['sym']}"):
                    _abrir_ficha(f["sym"], f["label"], categoria)
    return total, len(filas)


# ----------------------------- Ficha (modal) -----------------------------
def _cerrar_ficha():
    st.session_state.mkt_detalle = None


def _ir_a_trading(real: str, lado: str | None = None):
    st.session_state.activo_seleccionado = real
    st.session_state.nav_activo = "trading"
    if lado:
        st.session_state.ord_side = lado
    st.session_state.mkt_detalle = None
    st.rerun()


def _rng_html(titulo, lo, hi, val, dig, nota="") -> str:
    if lo is None or hi is None or hi <= lo:
        return ""
    pos = max(0, min(100, (val - lo) / (hi - lo) * 100))
    return (f"<div class='fic-rng'><div class='t'><span>{titulo}</span><span>{nota}</span></div>"
            f"<div class='bar'><div class='dot' style='left:{pos:.1f}%;'></div></div>"
            f"<div class='n'><span>{lo:,.{dig}f}</span><span>{hi:,.{dig}f}</span></div></div>")


def _r(k, v) -> str:
    return f"<div class='fic-r'><span class='k'>{k}</span><span class='v'>{v}</span></div>"


_GRAFICO_HTML = r"""
<div id="wrap" style="font-family:'Source Sans Pro',system-ui,sans-serif;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
    <div id="leyenda" style="color:#8b949e;font-size:12px;"></div>
    <div id="tabs" style="display:flex;gap:2px;background:#0f1620;border:1px solid #202a37;border-radius:8px;padding:2px;"></div>
  </div>
  <div id="chart" style="height:__H__px;"></div>
</div>
<style>
  body { margin:0; background:transparent; }
  #tabs button { background:transparent; border:none; color:#8b949e; font-size:12px; font-weight:600;
                 padding:4px 11px; border-radius:6px; cursor:pointer; }
  #tabs button:hover { color:#e6edf3; }
  #tabs button.on { background:#202a37; color:#e6edf3; }
</style>
<script src="https://cdn.jsdelivr.net/npm/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<script>
(function(){
  var D = __DATA__, DIG = __DIG__, SYM = __SYM__;
  var el = document.getElementById('chart');
  if (!window.LightweightCharts){ el.innerHTML = '<div style="color:#8b949e;font-size:12px;padding:20px;">No se pudo cargar el gráfico (sin internet).</div>'; return; }
  var ch = LightweightCharts.createChart(el, {
    autoSize: true,
    layout: { background: { type: 'solid', color: 'transparent' }, textColor: '#8b949e', fontSize: 11 },
    grid: { vertLines: { visible: false }, horzLines: { color: '#161d27' } },
    rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.12, bottom: 0.08 } },
    timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false },
    crosshair: { mode: 1, vertLine: { color: '#30363d', labelBackgroundColor: '#202a37' },
                 horzLine: { color: '#30363d', labelBackgroundColor: '#202a37' } },
    handleScroll: false, handleScale: false,
    localization: { priceFormatter: function(p){ return p.toLocaleString('en-US', {minimumFractionDigits: DIG, maximumFractionDigits: DIG}); } }
  });
  var serie = ch.addAreaSeries({ lineWidth: 2, priceLineVisible: false, lastValueVisible: true });
  var PER = [['1D','d'],['1S','w'],['1M',22],['3M',66],['6M',132],['1A',260]];
  var tabs = document.getElementById('tabs'), ley = document.getElementById('leyenda'), actual = null;
  var modo = 'd', horas = true;   // 'd' = 1 día (M5), 'w' = 1 semana (H1), número = días (D1)
  function fuente(){ return modo === 'd' ? D.m5 : (modo === 'w' ? D.h1 : D.d1); }
  function paso(){ return modo === 'd' ? 300 : (modo === 'w' ? 3600 : 86400); }
  var datos = [], sobre = false, raf = false;
  function fmt(v){ return v.toLocaleString('en-US', {minimumFractionDigits: DIG, maximumFractionDigits: DIG}); }
  function poner(k){
    modo = k; horas = (k === 'd' || k === 'w');
    datos = (typeof k === 'number' ? D.d1.slice(-k) : fuente()).slice();
    if (!datos.length) return;
    serie.setData(datos);
    colorear();
    ch.timeScale().fitContent();
  }
  function colorear(){
    var a = datos[0].value, b = datos[datos.length - 1].value, sube = b >= a;
    var c = sube ? '#3fb950' : '#f85149';
    serie.applyOptions({ lineColor: c, topColor: sube ? 'rgba(63,185,80,.28)' : 'rgba(248,81,73,.28)',
                         bottomColor: 'rgba(0,0,0,0)' });
    var p = (b / a - 1) * 100;
    actual = '<span style="color:' + c + ';font-weight:700;">' + (p >= 0 ? '+' : '') + p.toFixed(2) + '%</span> en el periodo' +
             ' &nbsp;<span style="color:#3fb950;">&#9679;</span> en vivo';
    if (!sobre) ley.innerHTML = actual;
  }
  // EN VIVO: el feed reenvía cada tick por BroadcastChannel('pj-ticks'); se mueve el
  // último punto (o se agrega uno al empezar otra hora / otro día). Bid, como MT5.
  function aplicarTick(t){
    if (!datos.length) return;
    var seg = paso(), ini = Math.floor(t.t / seg) * seg;
    var src = fuente(), ult = datos[datos.length - 1];
    var punto = {time: Math.max(ini, ult.time), value: t.b};
    if (punto.time > ult.time){ datos.push(punto); src.push(punto); }
    else { datos[datos.length - 1] = punto; src[src.length - 1] = punto; }
    if (raf) return; raf = true;
    requestAnimationFrame(function(){ raf = false; serie.update(datos[datos.length - 1]); colorear(); });
  }
  if ('BroadcastChannel' in window){
    new BroadcastChannel('pj-ticks').onmessage = function(ev){
      var t = ev.data && ev.data.t && ev.data.t[SYM];
      if (t && t.b && t.t) aplicarTick(t);
    };
  }
  PER.forEach(function(x, i){
    var b = document.createElement('button'); b.textContent = x[0];
    b.onclick = function(){ [].forEach.call(tabs.children, function(y){ y.className = ''; }); b.className = 'on'; poner(x[1]); };
    tabs.appendChild(b);
    if (x[0] === '1D'){ b.className = 'on'; }
  });
  poner(D.m5.length ? 'd' : 132);
  ch.subscribeCrosshairMove(function(pm){
    sobre = !!(pm && pm.time && pm.seriesData.get(serie));
    if (!sobre){ ley.innerHTML = actual; return; }
    var v = pm.seriesData.get(serie).value, f = new Date(pm.time * 1000);
    ley.innerHTML = '<span style="color:#e6edf3;font-weight:700;">' + fmt(v) + '</span> &nbsp;' +
      f.toLocaleDateString('es-CL', {day:'2-digit', month:'short', year:'numeric', timeZone:'UTC'}) +
      (horas ? ' ' + f.toISOString().substr(11, 5) : '');
  });
})();
</script>
"""


def _grafico(real: str, df_d1, df_h1, df_m5, dig: int, alto: int = 300):
    def _pts(df):
        if df is None or df.empty:
            return []
        return [{"time": int(ts.timestamp()), "value": round(float(v), dig)}
                for ts, v in df["close"].items()]
    data = {"d1": _pts(df_d1), "h1": _pts(df_h1), "m5": _pts(df_m5)}
    html = (_GRAFICO_HTML.replace("__DATA__", json.dumps(data))
            .replace("__DIG__", str(dig)).replace("__H__", str(alto))
            .replace("__SYM__", json.dumps(real)))
    components.html(html, height=alto + 40)


@st.dialog(" ", width="large", on_dismiss=_cerrar_ficha)
def _mostrar_ficha():
    det = st.session_state.get("mkt_detalle") or {}
    real, label, cat = det.get("sym"), det.get("label", ""), det.get("cat", "")
    if not real:
        return
    with MT5_LOCK:
        mt5.symbol_select(real, True)
        info0 = mt5.symbol_info(real)    # campos estáticos (dígitos, contrato, swaps...)
    if info0 is None:
        st.warning("No se pudo cargar la información del instrumento.")
        return
    dig = int(_g(info0, "digits") or 2)
    punto = float(_g(info0, "point") or 10 ** -dig)

    df = _serie(real, mt5.TIMEFRAME_D1, 260)
    h1 = _serie(real, mt5.TIMEFRAME_H1, 120)
    open_hoy = prev_close = wk_hi = wk_lo = atr_pct = None
    if df is not None and len(df) > 1:
        open_hoy = float(df["open"].iloc[-1])
        prev_close = float(df["close"].iloc[-2])
        wk_hi, wk_lo = float(df["high"].max()), float(df["low"].min())
        tr = (df["high"] - df["low"]).tail(14)
        atr_pct = float(tr.mean()) / float(df["close"].iloc[-1]) * 100 if len(tr) else None

    with st.container(key="fic_root"):
        # --- Cabecera ---
        desc = getattr(info0, "description", "") or ""
        st.html(
            f"<div class='fic-head'><span class='mkt-ic'>{icono_activo(real, 46)}</span><div>"
            f"<div class='fic-nm'>{label}</div><div class='fic-chips'>"
            f"<span class='fic-chip'>{real}</span><span class='fic-chip'>{cat}</span>"
            + (f"<span class='fic-chip'>{desc}</span>" if desc and desc.lower() != label.lower() else "")
            + "</div></div></div>"
        )

        # --- EN VIVO: precio + caja Vender / Comprar ---
        @st.fragment(run_every=intervalo("2s"))
        def _precio_vivo():
            with MT5_LOCK:
                tick = mt5.symbol_info_tick(real)
                info = mt5.symbol_info(real)
            bid = float(getattr(tick, "bid", 0) or _g(info, "bid") or 0)
            ask = float(getattr(tick, "ask", 0) or _g(info, "ask") or 0)
            t = int(getattr(tick, "time", 0) or 0)
            ch = (bid - prev_close) if prev_close else 0.0
            pct = (ch / prev_close * 100) if prev_close else 0.0
            f = {"sym": real, "ch": ch, "pct": pct}
            abierto = _abierto(t)
            hora = datetime.fromtimestamp(t, tz=timezone.utc).strftime("%d-%m %H:%M:%S") if t else "—"
            pip = punto * 10 if dig in (3, 5) else punto
            spread = (ask - bid) / pip if pip else 0
            unidad = "pips" if dig in (3, 5) else "pts"
            c1, c2 = st.columns([1.25, 1], vertical_alignment="center")
            with c1:
                st.html(
                    f"<div class='fic-pxrow'><span class='fic-px' {_live(real, 'px', d=dig, flash=1)}>"
                    f"{bid:,.{dig}f}</span>{_pill(f)}"
                    f"<span class='mkt-num' style='color:{_VERDE if ch >= 0 else _ROJO};font-size:14px;"
                    f"font-weight:700;' {_live(real, 'ch', d=dig)}>{ch:+,.{dig}f}</span></div>"
                    f"<div class='fic-pxsub'><span class='mkt-dot{'' if abierto else ' off'}'></span>&nbsp; "
                    f"{'Mercado abierto' if abierto else 'Mercado cerrado'} · último tick {hora} (hora del servidor)"
                    + (f" · cierre anterior {prev_close:,.{dig}f}" if prev_close else "") + "</div>"
                )
            with c2:
                v, c = st.columns(2, gap="small")
                with v:
                    with st.container(key="ficsd_sell"):
                        st.html(f"<div class='fic-side fic-sell'><div class='k'>VENDER</div>"
                                f"<div class='v' {_live(real, 'bid', d=dig)}>{bid:,.{dig}f}</div></div>")
                        if st.button("Vender", key="ficov_sell"):
                            _ir_a_trading(real, "SELL")
                with c:
                    with st.container(key="ficsd_buy"):
                        st.html(f"<div class='fic-side fic-buy'><div class='k'>COMPRAR</div>"
                                f"<div class='v' {_live(real, 'ask', d=dig)}>{ask:,.{dig}f}</div></div>")
                        if st.button("Comprar", key="ficov_buy"):
                            _ir_a_trading(real, "BUY")
                st.html(f"<div style='text-align:center;color:{_GRIS};font-size:11.5px;margin-top:-6px;'>"
                        f"Spread <b class='mkt-num' style='color:#e6edf3;' "
                        f"{_live(real, 'spr', pip=pip)}>{spread:,.1f}</b> {unidad}</div>")
        _precio_vivo()

        # --- Gráfico interactivo ---
        _grafico(real, df, h1, _serie(real, mt5.TIMEFRAME_M5, 288), dig)

        # --- Rendimiento por periodo ---
        if df is not None and len(df) > 1:
            closes = df["close"]
            last = float(closes.iloc[-1])

            def _ret(n):
                return (last / float(closes.iloc[-n - 1]) - 1) * 100 if len(closes) > n else None
            perf = {"1 día": _ret(1), "1 semana": _ret(5), "1 mes": _ret(22),
                    "3 meses": _ret(66), "6 meses": _ret(132), "1 año": _ret(252)}
            tope = max([abs(x) for x in perf.values() if x is not None] or [1]) or 1
            celdas = ""
            for k, v in perf.items():
                if v is None:
                    celdas += f"<div><div class='k'>{k}</div><div class='v' style='color:{_GRIS};'>—</div></div>"
                    continue
                c = _VERDE if v >= 0 else _ROJO
                ancho = abs(v) / tope * 50
                lado = f"left:50%;width:{ancho:.1f}%" if v >= 0 else f"right:50%;width:{ancho:.1f}%"
                celdas += (f"<div><div class='k'>{k}</div><div class='v' style='color:{c};'>{v:+.2f}%</div>"
                           f"<div class='b'><span style='{lado};background:{c};'></span></div></div>")
            st.html(f"<div class='fic-perf'>{celdas}</div>")

        # --- Estadísticas clave + especificaciones del contrato ---
        with MT5_LOCK:
            info = mt5.symbol_info(real) or info0
        bid = float(_g(info, "bid"))
        hi = float(_g(info, "bidhigh") or bid)
        lo = float(_g(info, "bidlow") or bid)
        col1, col2 = st.columns(2, gap="small")
        with col1:
            stats = ""
            if prev_close is not None:
                stats += _r("Cierre anterior", f"{prev_close:,.{dig}f}")
            if open_hoy is not None:
                stats += _r("Apertura", f"{open_hoy:,.{dig}f}")
            stats += _rng_html("Rango del día", min(lo, bid), max(hi, bid), bid, dig)
            if wk_hi is not None:
                dist = (bid / wk_hi - 1) * 100 if wk_hi else 0
                stats += _rng_html("Rango 52 semanas", wk_lo, wk_hi, bid, dig, f"{dist:+.1f}% del máximo")
            if atr_pct is not None:
                stats += _r("Volatilidad diaria (ATR 14)", f"{atr_pct:.2f}%")
            vol = _g(info, "volume") or _g(info, "volumereal")
            if vol:
                stats += _r("Volumen", f"{vol:,.0f}")
            st.html(f"<div class='fic-box'><h4>Estadísticas clave</h4>{stats}</div>")
        with col2:
            specs = ""
            contrato = _g(info0, "trade_contract_size")
            if contrato:
                specs += _r("Tamaño del contrato", f"{contrato:,.0f}")
            vmin, vstep, vmax = _g(info0, "volume_min"), _g(info0, "volume_step"), _g(info0, "volume_max")
            if vmin:
                specs += _r("Volumen mín. / paso", f"{vmin:g} / {vstep:g} lotes")
            if vmax:
                specs += _r("Volumen máximo", f"{vmax:,.0f} lotes")
            specs += _r("Tamaño del tick", f"{_g(info0, 'trade_tick_size') or punto:g}")
            base = getattr(info0, "currency_base", "") or ""
            prof = getattr(info0, "currency_profit", "") or ""
            marg = getattr(info0, "currency_margin", "") or ""
            if prof:
                specs += _r("Divisa de ganancia", prof)
            if marg or base:
                specs += _r("Divisa de margen", marg or base)
            sl, ss = _g(info0, "swap_long"), _g(info0, "swap_short")
            if sl or ss:
                specs += _r("Swap compra / venta", f"{sl:+.2f} / {ss:+.2f}")
            st.html(f"<div class='fic-box'><h4>Especificaciones del contrato</h4>{specs}</div>")

        # --- Acciones ---
        st.html("<div style='height:4px;'></div>")
        a1, a2, a3 = st.columns([1.4, 1, 1])
        with a1:
            with st.container(key="fic_operar"):
                if st.button("Operar " + label, icon=":material/candlestick_chart:", width="stretch"):
                    _ir_a_trading(real)
        with a2:
            if st.button("Agregar a mi lista", icon=":material/playlist_add:", width="stretch"):
                from components.buscador import _agregar_a_watchlist
                uid = (st.session_state.get("usuario_info") or {}).get("id")
                _agregar_a_watchlist(uid, {"name": real, "visible": real, "desc": label, "cat": cat})
                st.toast(f"{label} agregado a tu lista.")
        with a3:
            if st.button("Agregar a favoritos", icon=":material/star:", width="stretch"):
                from components.favoritos_bar import agregar_favorito
                agregar_favorito(real)


# Indicador "cargando" de la ficha. Se muestra EN EL NAVEGADOR en el mismo instante
# del clic (un st.spinner de Python recién aparecería cuando el servidor ya va a
# mitad del rerun) y se quita solo cuando el modal de la ficha está en el DOM.
_JS_CARGANDO = r"""
<script>
(function(){
  var P = window.parent, D;
  try { D = P.document; } catch(e) { return; }
  if (!D.getElementById('pj-mkt-load-css')){
    var st = D.createElement('style'); st.id = 'pj-mkt-load-css';
    st.textContent =
      '#pj-mkt-load{position:fixed;inset:0;z-index:999999;display:flex;align-items:center;justify-content:center;' +
      'background:rgba(5,8,14,.55);backdrop-filter:blur(3px);opacity:0;transition:opacity .18s ease;pointer-events:none;}' +
      '#pj-mkt-load.on{opacity:1;}' +
      '#pj-mkt-load .box{display:flex;flex-direction:column;align-items:center;gap:14px;background:#0d1117;' +
      'border:1px solid #30363d;border-radius:16px;padding:26px 34px;box-shadow:0 18px 50px rgba(0,0,0,.55);}' +
      '#pj-mkt-load .ring{width:46px;height:46px;border-radius:50%;' +
      'background:conic-gradient(from 0deg,rgba(255,75,75,0),#ff4b4b 55%,#ff8f00);' +
      '-webkit-mask:radial-gradient(farthest-side,transparent calc(100% - 5px),#000 calc(100% - 4px));' +
      'mask:radial-gradient(farthest-side,transparent calc(100% - 5px),#000 calc(100% - 4px));' +
      'animation:pjgira .8s linear infinite;}' +
      '#pj-mkt-load .t{color:#e6edf3;font:600 14px "Source Sans Pro",system-ui,sans-serif;}' +
      '#pj-mkt-load .s{color:#8b949e;font:12px "Source Sans Pro",system-ui,sans-serif;margin-top:-8px;}' +
      '@keyframes pjgira{to{transform:rotate(360deg);}}';
    D.head.appendChild(st);
  }
  var tope = null, obs = null;
  function ocultar(){
    var el = D.getElementById('pj-mkt-load');
    if (obs){ obs.disconnect(); obs = null; }
    if (tope){ clearTimeout(tope); tope = null; }
    if (!el) return;
    el.classList.remove('on');
    setTimeout(function(){ if (el.parentNode) el.parentNode.removeChild(el); }, 200);
  }
  function mostrar(nombre){
    ocultar();
    var el = D.createElement('div'); el.id = 'pj-mkt-load';
    el.innerHTML = '<div class="box"><div class="ring"></div><div class="t"></div>' +
                   '<div class="s">Cargando precios, gráfico y estadísticas</div></div>';
    el.querySelector('.t').textContent = nombre ? 'Abriendo ' + nombre + '…' : 'Abriendo ficha…';
    D.body.appendChild(el);
    requestAnimationFrame(function(){ el.classList.add('on'); });
    obs = new MutationObserver(function(){ if (D.querySelector('.st-key-fic_root')) ocultar(); });
    obs.observe(D.body, {childList: true, subtree: true});
    tope = setTimeout(ocultar, 20000);            // respaldo: nunca queda pegado
  }
  if (P.__pjMktLoadFn) D.removeEventListener('click', P.__pjMktLoadFn, true);
  P.__pjMktLoadFn = function(e){
    var b = e.target.closest && e.target.closest('[class*="st-key-mktclk_"] button');
    if (!b) return;
    var cont = b.closest('[class*="st-key-mktrow_"], [class*="st-key-mktcard_"]');
    var nm = cont && cont.querySelector('.mkt-nm b, .mkt-card-nm');
    mostrar(nm ? nm.textContent.trim() : '');
  };
  D.addEventListener('click', P.__pjMktLoadFn, true);   // captura: sin frenar el clic
})();
</script>
"""


# ----------------------------- Página -----------------------------
def renderizar_panel_mercados(main=None):
    inicializar_mt5()
    st.html(_CSS)
    en_vivo = intervalo("x") is None
    st.html(
        "<div class='mkt-hdr'><div><div class='mkt-title'>Mercados</div>"
        "<div class='mkt-sub'>Cotizaciones de MetaTrader 5 · variación respecto del cierre "
        "anterior · haz clic en un instrumento para ver su ficha</div></div>"
        f"<span class='mkt-live'><span class='mkt-dot{'' if en_vivo else ' off'}'></span>"
        f"{'Datos en tiempo real' if en_vivo else 'Actualización cada 3 s'}</span></div>"
    )

    @st.fragment(run_every=intervalo("3s", "30s"))
    def _resumen_vivo():
        _resumen()
    _resumen_vivo()
    st.html("<div style='height:6px;'></div>")

    categorias = list(_CATALOGO.keys())
    conteo = {c: len(_items(c)) for c in categorias}
    c_tabs, c_q, c_ord = st.columns([3.2, 1.3, 0.9], vertical_alignment="bottom")
    with c_tabs:
        with st.container(key="mkt_tabs"):
            cat = st.segmented_control(
                "Categoría", categorias, default=categorias[0], key="mkt_cat",
                format_func=lambda c: f"{c}  {conteo.get(c, 0)}", label_visibility="collapsed",
            ) or categorias[0]
    with c_q:
        st.text_input("Buscar", key="mkt_q", placeholder="Filtrar instrumentos…",
                      label_visibility="collapsed", icon=":material/search:")
    with c_ord:
        st.selectbox("Ordenar", _ORDENES, key="mkt_orden", label_visibility="collapsed")

    @st.fragment(run_every=intervalo("3s", "30s"))
    def _tabla_en_vivo():
        categoria = st.session_state.get("mkt_cat") or categorias[0]
        n = len(_items(categoria))
        st.html(f"<div class='mkt-nota'><span class='ico'>local_fire_department</span>"
                f"<span>Mostrando <b>los {n} {categoria.lower()} más seguidos del mercado</b></span></div>")
        total, mostrados = _render_tabla(categoria)
        st.html(f"<div class='mkt-pie'>{mostrados} de {total} instrumentos · {categoria} · "
                f"actualizado {datetime.now().strftime('%H:%M:%S')}</div>")
    _tabla_en_vivo()

    # Script del indicador "cargando" (fuera del flujo, no ocupa espacio)
    with st.container(key="mkt_loadjs"):
        components.html(_JS_CARGANDO, height=0)

    # El modal se abre con la bandera y se renderiza AQUÍ (fuera de los fragmentos en
    # vivo) para no chocar con su auto-refresco (evita pantallas en blanco).
    if st.session_state.get("mkt_detalle"):
        _mostrar_ficha()
