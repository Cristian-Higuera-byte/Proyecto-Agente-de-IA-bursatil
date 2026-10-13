"""
resumen_panel.py
----------------
Vista "Resumen": dashboard del portafolio (sección F). Tarjetas KPI con icono,
acento de color y micro-interacción (hover), nivel de margen como barra, curva de
balance con selector de periodo (interactivo) y exposición por activo. Todos los
números salen de tools.portafolio_stats (datos reales de MT5). Estética P&J:
fondo oscuro, números grandes, verde/rojo según signo, acento naranja del logo.

Limitaciones honestas que la propia UI indica:
  - Drawdown mostrado = de BALANCE (MT5 no guarda snapshots de equity).
  - Dividendos: si el bróker/demo no generó eventos, muestra "sin dividendos".
"""
import html
import time

import streamlit as st

from components.live_feed import intervalo as _intervalo
from tools.mt5_bridge import inicializar_mt5
from tools import portafolio_stats

# OJO (Streamlit 1.64): no escribir etiquetas HTML dentro de este CSS, ni en
# comentarios: st.html las sanea con DOMPurify y descarta el bloque completo.
_CSS = """
<style>
  .st-key-rs_wrap { max-width:1200px; margin-left:auto; margin-right:auto; width:100%; }
  .st-key-rs_wrap [data-testid="stVerticalBlock"] { gap:22px; }
  .rmi { font-family:'Material Symbols Rounded'; font-weight:400; line-height:1;
         background:linear-gradient(135deg,#ff6a3d,#ff8f00); -webkit-background-clip:text;
         background-clip:text; color:transparent; font-size:20px; }

  .rs-head { display:flex; align-items:center; gap:12px; margin-bottom:2px; }
  .rs-head .ic { width:42px; height:42px; border-radius:12px; display:flex; align-items:center;
      justify-content:center; background:linear-gradient(135deg,rgba(255,75,75,.16),rgba(255,143,0,.16));
      border:1px solid #2a2320; flex:0 0 auto; }
  .rs-title { font-size:22px; font-weight:800; color:#fff; letter-spacing:-.2px; }
  .rs-sub { font-size:12.5px; color:#8b949e; margin-top:2px; }

  /* ---- Rejilla de tarjetas KPI ---- */
  .rs-grid { display:grid; grid-template-columns:repeat(4,1fr); column-gap:18px; row-gap:14px; }
  @media (max-width:1100px){ .rs-grid { grid-template-columns:repeat(2,1fr); column-gap:16px; row-gap:14px; } }
  .rs-card { background:linear-gradient(180deg,#111926,#0d131d); border:1px solid #202a37;
      border-radius:16px; padding:15px 17px 16px; position:relative; overflow:hidden;
      box-sizing:border-box; transition:transform .15s ease, border-color .15s ease, box-shadow .15s ease; }
  .rs-card::after { content:""; position:absolute; left:0; top:0; bottom:0; width:3px;
      background:var(--acc,#30363d); opacity:.9; }
  .rs-card:hover { transform:translateY(-3px); border-color:#30405a;
      box-shadow:0 10px 26px rgba(0,0,0,.35); }
  .rs-ctop { display:flex; align-items:center; justify-content:space-between; gap:8px; }
  .rs-k { font-size:10.5px; color:#8b949e; font-weight:700; text-transform:uppercase; letter-spacing:.5px; }
  .rs-cico { width:30px; height:30px; border-radius:9px; display:flex; align-items:center; justify-content:center;
      background:var(--icbg,#182130); flex:0 0 auto; }
  .rs-cico .m { font-family:'Material Symbols Rounded'; font-size:17px; line-height:1; color:var(--icfg,#8b949e); }
  .rs-v { font-size:23px; font-weight:800; color:#e6edf3; margin-top:11px; font-variant-numeric:tabular-nums;
      letter-spacing:-.3px; display:flex; align-items:baseline; gap:4px; }
  .rs-v .u { font-size:13px; font-weight:700; color:#6b7686; }
  .rs-v.sm { font-size:19px; }
  .rs-foot { font-size:11.5px; color:#8b949e; margin-top:7px; font-variant-numeric:tabular-nums; line-height:1.45; }
  .rs-up { color:#2ebd85; } .rs-down { color:#f6465d; } .rs-neu { color:#e6edf3; }
  .rs-arrow { font-size:15px; margin-right:1px; }
  .rs-pill { display:inline-block; font-size:11px; font-weight:700; padding:2px 8px; border-radius:999px;
      margin-left:7px; font-variant-numeric:tabular-nums; vertical-align:middle; }
  .rs-pill.up { background:rgba(46,189,133,.14); color:#2ebd85; }
  .rs-pill.down { background:rgba(246,70,93,.14); color:#f6465d; }

  /* ---- Bloques anchos (margen + curva + exposición) ---- */
  .rs-panel { background:linear-gradient(180deg,#111926,#0d131d); border:1px solid #202a37;
      border-radius:16px; padding:18px 20px; box-sizing:border-box; }
  .rs-panel-t { font-size:14px; font-weight:800; color:#e6edf3; margin-bottom:12px;
      display:flex; align-items:center; gap:8px; }
  .rs-panel-t small { color:#8b949e; font-weight:600; font-size:11.5px; }
  .rs-panel-t .right { margin-left:auto; font-weight:700; font-size:12.5px; font-variant-numeric:tabular-nums; }

  /* Barra de nivel de margen */
  .rs-ml-top { display:flex; align-items:baseline; gap:10px; }
  .rs-ml-v { font-size:26px; font-weight:800; font-variant-numeric:tabular-nums; }
  .rs-ml-tag { font-size:11px; font-weight:700; padding:3px 9px; border-radius:999px; }
  .rs-ml-bar { height:9px; border-radius:5px; background:#182130; overflow:hidden; margin:12px 0 6px; }
  .rs-ml-fill { height:100%; border-radius:5px; }

  .rs-expo { width:100%; border-collapse:collapse; }
  .rs-expo td, .rs-expo th { padding:9px 6px; font-size:12.5px; border-bottom:1px solid #182130;
      font-variant-numeric:tabular-nums; }
  .rs-expo th { color:#8b949e; font-weight:700; text-transform:uppercase; font-size:10px;
      letter-spacing:.5px; text-align:right; }
  .rs-expo th:first-child, .rs-expo td:first-child { text-align:left; }
  .rs-expo tr { transition:background .12s ease; }
  .rs-expo tbody tr:hover { background:#141c28; }
  .rs-expo td { color:#c9d1d9; }
  .rs-expo .nm { font-weight:700; color:#e6edf3; }
  .rs-expo .bar { height:7px; border-radius:4px; background:linear-gradient(90deg,#3fb950,#2ea043); }
  .rs-barwrap { background:#182130; border-radius:4px; overflow:hidden; width:100%; }

  .rs-note { color:#6b7686; font-size:11px; margin-top:8px; line-height:1.5; }
  .rs-empty { color:#8b949e; font-size:13px; padding:26px 10px; text-align:center; }

  /* Panel de la curva: el selector de periodo + el gráfico como un solo bloque */
  .st-key-rs_curvapanel { background:linear-gradient(180deg,#111926,#0d131d);
      border:1px solid #202a37; border-radius:16px; padding:16px 20px 18px; box-sizing:border-box; }
  .st-key-rs_curvapanel [data-testid="stVerticalBlock"] { gap:14px; }
  .st-key-rs_curvapanel div[data-testid="stMarkdownContainer"] { margin-bottom:0 !important; }
  /* Selector de periodo de la curva (segmented_control) */
  .st-key-rs_periodo [data-baseweb="segmented-control"],
  .st-key-rs_periodo [role="radiogroup"] { background:#0d131d !important; }
  .st-key-rs_periodo button[aria-checked="true"] { background:#1b2634 !important; color:#fff !important; }
</style>
"""

# (acento, icono, fondo icono, color icono)
_ACC = {
    "cap":  ("#58a6ff", "account_balance_wallet", "rgba(88,166,255,.14)", "#58a6ff"),
    "up":   ("#2ebd85", "trending_up",            "rgba(46,189,133,.14)", "#2ebd85"),
    "down": ("#f6465d", "trending_down",          "rgba(246,70,93,.14)",  "#f6465d"),
    "exp":  ("#f0b429", "pie_chart",              "rgba(240,180,41,.14)", "#f0b429"),
    "risk": ("#f85149", "shield",                 "rgba(248,81,73,.14)",  "#f85149"),
    "fee":  ("#8b949e", "receipt_long",           "rgba(139,148,158,.14)","#b4bdc8"),
    "dd":   ("#ff8f00", "stacked_line_chart",     "rgba(255,143,0,.14)",  "#ff8f00"),
    "acum": ("#a371f7", "savings",                "rgba(163,113,247,.14)","#a371f7"),
}


def _compact(x, moneda="", signo=False):
    """Formatea montos grandes de forma compacta (1.2M, 31.6K) y legible."""
    a = abs(x)
    s = ("+" if (signo and x > 0) else ("-" if x < 0 else ""))
    if a >= 1_000_000:
        cuerpo = f"{a/1_000_000:,.2f}M"
    elif a >= 10_000:
        cuerpo = f"{a/1_000:,.1f}K"
    else:
        cuerpo = f"{a:,.2f}"
    return f"{s}{cuerpo}" + (f" {moneda}" if moneda else "")


def _card(clave, k, valor, unidad="", foot="", pill_html="", arrow=False, valcls="rs-neu",
          val_attrs=""):
    """val_attrs: atributos data-pj-* para que el feed pinte el valor EN VIVO
    (sub-segundo, sin rerun) igual que el resto del dashboard."""
    acc, ico, icbg, icfg = _ACC[clave]
    ar = ""
    if arrow:
        ar = ("<span class='rs-arrow'>▲</span>" if valcls == "rs-up"
              else "<span class='rs-arrow'>▼</span>" if valcls == "rs-down" else "")
    u = f"<span class='u'>{unidad}</span>" if unidad else ""
    foot_html = f"<div class='rs-foot'>{foot}</div>" if foot else ""
    return (
        f"<div class='rs-card' style='--acc:{acc};--icbg:{icbg};--icfg:{icfg}'>"
        f"<div class='rs-ctop'><div class='rs-k'>{k}</div>"
        f"<div class='rs-cico'><span class='m'>{ico}</span></div></div>"
        f"<div class='rs-v'><span class='{valcls}' {val_attrs}>{ar}{valor}</span>{u}{pill_html}</div>"
        f"{foot_html}</div>"
    )


def _vcls(x):
    return "rs-up" if x > 0 else ("rs-down" if x < 0 else "rs-neu")


def _curva_svg(curva, moneda):
    """Curva de balance como SVG (área con degradado). Estática; se redibuja en
    cada refresco. El color depende de si el periodo sube o baja."""
    puntos = [b for _t, b in curva]
    if len(puntos) < 2:
        return ("<div class='rs-empty'>Aún no hay suficientes operaciones en este "
                "periodo para dibujar la curva.</div>")
    lo, hi = min(puntos), max(puntos)
    rng = (hi - lo) or 1.0
    W, H, pad = 1000, 230, 12
    n = len(puntos)
    xs = [pad + (W - 2 * pad) * i / (n - 1) for i in range(n)]
    ys = [H - pad - (H - 2 * pad) * (b - lo) / rng for b in puntos]
    linea = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(zip(xs, ys)))
    area = (f"M{xs[0]:.1f},{H - pad:.1f} "
            + " ".join(f"L{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
            + f" L{xs[-1]:.1f},{H - pad:.1f} Z")
    sube = puntos[-1] >= puntos[0]
    col = "#2ebd85" if sube else "#f6465d"
    # Línea base punteada al nivel inicial del periodo + punto final resaltado.
    y0 = ys[0]
    return (
        f"<svg viewBox='0 0 {W} {H}' preserveAspectRatio='none' style='width:100%;height:230px;display:block'>"
        f"<defs><linearGradient id='rsg' x1='0' y1='0' x2='0' y2='1'>"
        f"<stop offset='0%' stop-color='{col}' stop-opacity='.30'/>"
        f"<stop offset='100%' stop-color='{col}' stop-opacity='0'/></linearGradient></defs>"
        f"<line x1='{pad}' y1='{y0:.1f}' x2='{W-pad}' y2='{y0:.1f}' stroke='#2b3550' "
        f"stroke-width='1' stroke-dasharray='4 5'/>"
        f"<path d='{area}' fill='url(#rsg)'/>"
        f"<path d='{linea}' fill='none' stroke='{col}' stroke-width='2.2' "
        f"stroke-linejoin='round' stroke-linecap='round'/>"
        f"<circle cx='{xs[-1]:.1f}' cy='{ys[-1]:.1f}' r='4.5' fill='{col}'/>"
        f"<circle cx='{xs[-1]:.1f}' cy='{ys[-1]:.1f}' r='9' fill='{col}' fill-opacity='.22'/></svg>"
        f"<div style='display:flex;justify-content:space-between;color:#8b949e;"
        f"font-size:11px;margin-top:6px;font-variant-numeric:tabular-nums'>"
        f"<span>mín {lo:,.2f}</span><span>máx {hi:,.2f} {moneda}</span></div>"
    )


_PERIODOS = {"7 días": 7, "30 días": 30, "90 días": 90, "Todo": None}


def renderizar_panel_resumen(main=None):
    inicializar_mt5()
    st.html(_CSS)

    with st.container(key="rs_wrap"):
        st.markdown(
            "<div class='rs-head'><div class='ic'><span class='rmi'>dashboard</span></div>"
            "<div><div class='rs-title'>Resumen</div>"
            "<div class='rs-sub'>Rendimiento y riesgo del portafolio en tiempo real</div></div></div>",
            unsafe_allow_html=True,
        )

        # Con el feed activo, los valores de CUENTA (equity, flotante, nivel de margen)
        # se pintan en vivo por el feed (data-pj-acc), sin rerun; el fragmento solo
        # recalcula lo que necesita cómputo (realizado, exposición, curva) cada pocos s.
        @st.fragment(run_every=_intervalo("2s", "4s"))
        def _cuerpo():
            s = portafolio_stats.calcular()
            if "error" in s:
                st.warning("No se pudo conectar con MetaTrader 5. Abre el terminal "
                           "con la cuenta iniciada para ver tu portafolio.")
                return
            m = s["moneda"]
            cap, pnl, com = s["capital"], s["pnl"], s["comisiones"]
            exp, rie, dd = s["exposicion"], s["riesgo"], s["drawdown"]
            div, rent = s["dividendos"], s["rentabilidad"]

            # ---------- Fila 1 ----------
            d_tot, mes_tot = pnl["dia"]["total"], pnl["mes"]["total"]
            pct = rent["pct"]
            pill = f"<span class='rs-pill {'up' if pct >= 0 else 'down'}'>{pct:+.2f}%</span>"
            # Flotante EN VIVO (feed): mismo dato que el P/G de la barra superior.
            flot_live = ("<span data-pj-acc='profit' data-pj-fmt='signed' "
                         "data-pj-color='1'>{:+,.2f}</span>").format(pnl['dia']['flotante'])
            fila1 = [
                _card("cap", "Capital (equity)", f"{cap['equity']:,.2f}", "",
                      f"Saldo {cap['balance']:,.2f} · Libre {cap['margen_libre']:,.2f}",
                      val_attrs=f"data-pj-acc='equity' data-pj-base='{cap['equity']:.2f}'"),
                _card("up" if d_tot >= 0 else "down", "P&amp;L diario",
                      _compact(d_tot, signo=True), m,
                      f"Realizado {pnl['dia']['realizado']:+,.2f} · Flot. {flot_live} "
                      f"· {pnl['dia']['cierres']} cierres", arrow=True, valcls=_vcls(d_tot)),
                _card("up" if mes_tot >= 0 else "down", "P&amp;L mensual",
                      _compact(mes_tot, signo=True), m,
                      f"Realizado {pnl['mes']['realizado']:+,.2f} · Flot. {flot_live} "
                      f"· {pnl['mes']['cierres']} cierres", arrow=True, valcls=_vcls(mes_tot)),
                _card("acum", "Rentabilidad acumulada", _compact(rent['abs'], signo=True), m,
                      f"Depósito inicial {cap['deposito_inicial']:,.2f} {m}",
                      pill_html=pill, valcls=_vcls(rent['abs'])),
            ]

            # ---------- Fila 2 ----------
            sin_sl = rie["sin_sl"]
            sinsl_txt = f"{sin_sl} sin stop" if sin_sl else "todas con stop"
            apal = (exp["total"] / cap["equity"]) if cap["equity"] else 0.0
            com_tot = com["total"] + com["swap_total"]
            # Drawdown: equity REAL si ya hay snapshots (Tanda 2); si no, el de balance.
            if dd["equity_disponible"]:
                dd_pct, dd_abs_v, dd_lbl = dd["equity_pct"], dd["equity_abs"], "Drawdown (equity)"
                dd_base = f"Caída máx. {dd_abs_v:,.2f} {m} · {dd['equity_puntos']} muestras"
            else:
                dd_pct, dd_abs_v, dd_lbl = dd["balance_pct"], dd["balance_abs"], "Drawdown (balance)"
                dd_base = f"Caída máx. {dd_abs_v:,.2f} {m} · equity acumulando…"
            dd_txt = f"-{dd_pct:.2f}%" if dd_pct else "0%"
            div_txt = (_compact(div['total'], m, signo=True) if abs(div["total"]) > 1e-9
                       else "Sin dividendos")
            fila2 = [
                _card("exp", "Exposición total", _compact(exp['total']), m,
                      f"Largos {_compact(exp['largos'])} · Cortos {_compact(exp['cortos'])} "
                      f"· {apal:.1f}× equity", valcls="rs-neu"),
                _card("risk", "Riesgo definido", _compact(rie['definido'], signo=False), m,
                      f"Margen usado {rie['margen_usado']:,.2f} · {sinsl_txt}", valcls="rs-down"),
                _card("fee", "Comisiones y swaps", f"{com_tot:,.2f}", m,
                      f"Mes {(com['mes'] + com['swap_mes']):,.2f} · Hoy {(com['hoy'] + com['swap_hoy']):,.2f}",
                      valcls="rs-down" if com_tot < 0 else "rs-neu"),
                _card("dd", dd_lbl, dd_txt, "",
                      f"{dd_base} · Div. {div_txt}",
                      valcls="rs-down" if dd_pct else "rs-neu"),
            ]
            st.markdown("<div class='rs-grid'>" + "".join(fila1 + fila2) + "</div>",
                        unsafe_allow_html=True)

            # ---------- Nivel de margen (barra) ----------
            nivel = rie["margin_level"]
            if nivel:
                if nivel >= 300:
                    tcol, tbg, tlbl = "#2ebd85", "rgba(46,189,133,.14)", "Saludable"
                elif nivel >= 150:
                    tcol, tbg, tlbl = "#f0b429", "rgba(240,180,41,.14)", "Moderado"
                else:
                    tcol, tbg, tlbl = "#f6465d", "rgba(246,70,93,.14)", "En riesgo"
                # Barra: 100% (cierre forzoso) a 1000%+ como tope visual.
                ancho = max(4, min(100, nivel / 1000 * 100))
                st.markdown(
                    "<div class='rs-panel'><div class='rs-panel-t'>Nivel de margen "
                    "<small>(equity ÷ margen usado)</small></div>"
                    "<div class='rs-ml-top'>"
                    f"<span class='rs-ml-v' style='color:{tcol}' data-pj-acc='margin_level' "
                    f"data-pj-fmt='pct'>{nivel:,.0f}%</span>"
                    f"<span class='rs-ml-tag' style='color:{tcol};background:{tbg}'>{tlbl}</span></div>"
                    f"<div class='rs-ml-bar'><div class='rs-ml-fill' style='width:{ancho:.0f}%;"
                    f"background:linear-gradient(90deg,{tcol},{tcol}cc)'></div></div>"
                    "<div class='rs-note'>Por debajo de 100% hay cierre forzoso (stop out). "
                    "Cuanto más alto, más holgura ante movimientos en contra.</div></div>",
                    unsafe_allow_html=True,
                )

            # ---------- Curva de balance con selector de periodo (interactivo) ----------
            # El selector y la curva van DENTRO del mismo contenedor (rs_curvapanel)
            # para que se lean como un solo bloque (el selector pertenece al gráfico).
            with st.container(key="rs_curvapanel"):
                periodo = st.segmented_control(
                    "Periodo", list(_PERIODOS.keys()), default="Todo",
                    key="rs_periodo", label_visibility="collapsed")
                dias = _PERIODOS.get(periodo or "Todo")
                curva = s["curva"]
                if dias is not None:
                    corte = time.time() - dias * 86400
                    curva = [(t, b) for t, b in curva if t >= corte] or s["curva"][-2:]
                var = (curva[-1][1] - curva[0][1]) if len(curva) >= 2 else 0.0
                vcls = _vcls(var)
                st.markdown(
                    "<div class='rs-panel-t'>Curva de balance "
                    "<small>(balance realizado acumulado)</small>"
                    f"<span class='right {vcls}'>{var:+,.2f} {m} en el periodo</span></div>"
                    + _curva_svg(curva, m),
                    unsafe_allow_html=True,
                )

            # ---------- Exposición por activo ----------
            filas = exp["por_activo"]
            if filas:
                maxn = max((r["notional"] for r in filas), default=1.0) or 1.0
                total = exp["total"] or 1.0
                cuerpo = ""
                for r in filas:
                    w = max(3, int(r["notional"] / maxn * 100))
                    share = r["notional"] / total * 100
                    cuerpo += (
                        f"<tr><td class='nm'>{html.escape(str(r['nombre']))}</td>"
                        f"<td>{r['volumen']:,.2f}</td>"
                        f"<td>{_compact(r['notional'], m)}</td>"
                        f"<td>{share:.0f}%</td>"
                        f"<td style='width:34%'><div class='rs-barwrap'>"
                        f"<div class='bar' style='width:{w}%'></div></div></td></tr>")
                st.markdown(
                    "<div class='rs-panel'><div class='rs-panel-t'>Exposición por activo</div>"
                    "<table class='rs-expo'><thead><tr><th>Activo</th><th>Lotes</th>"
                    "<th>Notional</th><th>% cartera</th><th></th></tr></thead>"
                    f"<tbody>{cuerpo}</tbody></table></div>",
                    unsafe_allow_html=True,
                )

            if dd["equity_disponible"]:
                dd_nota = (f"Drawdown de equity real calculado sobre {dd['equity_puntos']} "
                           "muestras registradas en segundo plano (incluye el flotante de "
                           "posiciones abiertas). ")
            else:
                dd_nota = ("Drawdown de balance por ahora; el de equity real se está "
                           "registrando en segundo plano y aparecerá al reunir más muestras "
                           "(requiere el servidor de datos encendido). ")
            st.markdown(
                f"<div class='rs-note'>{dd_nota}Dividendos según los ajustes que reporte el "
                "bróker; en demo pueden no existir. P&amp;L, comisiones, swaps y exposición "
                "salen de operaciones reales de MetaTrader 5.</div>",
                unsafe_allow_html=True,
            )

        _cuerpo()
