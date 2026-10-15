"""Piezas HTML de Mercados: mini-gráfico, pastilla de variación, rango del día, fila de la tabla y tarjeta."""
import base64

import MetaTrader5 as mt5  # type: ignore[import-untyped]

from componentes_plataforma.iconos import icono_activo   # íconos estilo XM (comunes)
from componentes_plataforma.flujo_vivo import attrs as _live
from componentes_plataforma.mercado_datos import historial_sparkline as _historial_sparkline
from componentes_plataforma.mercados.broker import esta_abierto, serie
from componentes_plataforma.mercados.constantes import ROJO, VERDE


def svg_spark(vals, w=104, h=34, area=True) -> str:
    """Mini-gráfico como <img> data-URI (st.html sanea el SVG en línea)."""
    if not vals or len(vals) < 2:
        return f"<span style='display:inline-block;width:{w}px;height:{h}px;'></span>"
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    n = len(vals)
    pts = [(i * w / (n - 1), h - 3 - (v - lo) / rng * (h - 6)) for i, v in enumerate(vals)]
    col = VERDE if vals[-1] >= vals[0] else ROJO
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


def pill(f) -> str:
    sube = f["ch"] >= 0
    col, bg = (VERDE, "rgba(63,185,80,.12)") if sube else (ROJO, "rgba(248,81,73,.12)")
    txt = f"▲ +{f['pct']:.2f}%" if sube else f"▼ {f['pct']:.2f}%"
    return (f"<span class='mkt-pill' style='color:{col};background:{bg};' "
            f"{_live(f['sym'], 'pct', pill=1)}>{txt}</span>")


def rango_html(f) -> str:
    d = f["dig"]
    pos = 50.0 if f["hi"] <= f["lo"] else (f["last"] - f["lo"]) / (f["hi"] - f["lo"]) * 100
    return (f"<div class='mkt-rng'><span class='mkt-num'>{f['lo']:,.{d}f}</span>"
            f"<div class='bar'><div class='dot' style='left:{max(0, min(100, pos)):.1f}%;'></div></div>"
            f"<span class='mkt-num'>{f['hi']:,.{d}f}</span></div>")


def fila_html(f) -> str:
    d = f["dig"]
    col = VERDE if f["ch"] >= 0 else ROJO
    h1 = serie(f["sym"], mt5.TIMEFRAME_H1, 120)
    spark = svg_spark([float(x) for x in h1["close"].tolist()] if h1 is not None else [], 104, 30, area=False)
    abierto = esta_abierto(f["t"])
    estado = (f"<span class='mkt-est'><span class='mkt-dot{'' if abierto else ' off'}'></span>"
              f"{'Abierto' if abierto else 'Cerrado'}</span>")
    return (
        "<div class='mkt-row'>"
        f"<div><div class='mkt-nm'><span class='mkt-ic'>{icono_activo(f['sym'], 32)}</span>"
        f"<div style='min-width:0;'><b>{f['label']}</b><small>{f['sym']}</small></div></div></div>"
        f"<div class='mkt-r mkt-num' style='font-weight:700;' "
        f"{_live(f['sym'], 'px', d=d, flash=1)}>{f['last']:,.{d}f}</div>"
        f"<div class='mkt-r mkt-num' style='color:{col};' {_live(f['sym'], 'ch', d=d)}>{f['ch']:+,.{d}f}</div>"
        f"<div class='mkt-r'>{pill(f)}</div>"
        f"<div>{rango_html(f)}</div>"
        f"<div style='display:flex;justify-content:center;'>{spark}</div>"
        f"<div style='display:flex;align-items:center;justify-content:space-between;'>{estado}"
        "<span class='mkt-chev'>›</span></div>"
        "</div>"
    )


def tarjeta_html(f, tag: str) -> str:
    d = f["dig"]
    # Mini-gráfico EN VIVO: semilla M1 (últimos 30 min) y el feed agrega cada tick
    vals = _historial_sparkline(f["sym"])
    semilla = ",".join(f"{v:.6g}" for v in vals)
    spark = (f"<span data-pj-spark='{f['sym']}' data-pj-vals='{semilla}'>"
             f"{svg_spark(vals, 92, 40)}</span>")
    return (
        "<div class='mkt-card'>"
        f"<div class='mkt-card-top'><span class='mkt-ic'>{icono_activo(f['sym'], 28)}</span>"
        f"<div><div class='mkt-card-nm'>{f['label']}</div><div class='mkt-card-sym'>{f['sym']}</div></div>"
        f"<span class='mkt-card-tag'>{tag}</span></div>"
        f"<div class='mkt-card-px' {_live(f['sym'], 'px', d=d, flash=1)}>{f['last']:,.{d}f}</div>"
        f"<div class='mkt-card-bot'>{pill(f)}{spark}</div>"
        "</div>"
    )
