"""
journal_panel.py
----------------
Vista "Diario" (Trading Journal, sección E): registro automático de operaciones
cerradas desde MT5 + métricas (win rate, profit factor, R/R, expectancy, drawdown)
+ ficha por operación con mini-gráfico auto-generado y notas editables (estrategia,
emoción, razón) y R/R planificado/realizado.

Estética alineada con el historial de la vista Inicio (tabla `pos`, íconos de
activo, pills BUY/SELL, verde/rojo con la paleta P&J). Datos de journal_stats /
journal_store.
"""
import html
from datetime import datetime

import streamlit as st

from components.iconos import icono_activo
from tools.mt5_bridge import inicializar_mt5, obtener_info_cuenta, obtener_velas_rango
from tools import journal_stats, journal_store

# Paleta (P&J): verde #3fb950, rojo #f85149, azul #58a6ff, naranja #ff8f00.
_UP, _DN, _AZ, _NA, _TX, _GR = "#3fb950", "#f85149", "#58a6ff", "#ff8f00", "#e6edf3", "#8b949e"

# OJO (Streamlit 1.64): no escribir etiquetas HTML dentro de este CSS, ni en
# comentarios: st.html las sanea con DOMPurify y descarta el bloque completo.
_CSS = """
<style>
  .st-key-jr_wrap { max-width:1200px; margin-left:auto; margin-right:auto; width:100%; }
  .st-key-jr_wrap [data-testid="stVerticalBlock"] { gap:18px; }
  .jrmi { font-family:'Material Symbols Rounded'; font-weight:400; line-height:1;
         background:linear-gradient(135deg,#ff6a3d,#ff8f00); -webkit-background-clip:text;
         background-clip:text; color:transparent; font-size:20px; }
  .jr-head { display:flex; align-items:center; gap:12px; margin-bottom:2px; }
  .jr-head .ic { width:42px; height:42px; border-radius:12px; display:flex; align-items:center;
      justify-content:center; background:linear-gradient(135deg,rgba(255,75,75,.16),rgba(255,143,0,.16));
      border:1px solid #2a2320; flex:0 0 auto; }
  .jr-title { font-size:22px; font-weight:800; color:#fff; letter-spacing:-.2px; }
  .jr-sub { font-size:12.5px; color:#8b949e; margin-top:2px; }

  .jr-sec { display:flex; align-items:baseline; gap:10px; padding:2px 2px 2px; }
  .jr-sec h3 { margin:0; color:#e6edf3; font-size:15px; font-weight:800; }
  .jr-sec .s { color:#8b949e; font-size:12px; }

  /* Tarjeta contenedora (igual que el historial de Inicio) */
  .st-key-jr_card, .st-key-jr_ficha {
      background:#0f1620; border:1px solid #202a37; border-radius:18px; padding:6px 0; }
  .st-key-jr_ficha { padding:16px 18px 18px; }

  /* Resumen de métricas (estilo hist-sum de Inicio), repartido en todo el ancho */
  .jr-sum { display:grid; grid-template-columns:repeat(6,1fr); gap:18px;
      padding:16px 20px 18px; border-bottom:1px solid #1b2430; }
  @media (max-width:900px){ .jr-sum { grid-template-columns:repeat(3,1fr); } }
  .jr-sum .it { display:flex; flex-direction:column; gap:3px; min-width:0; }
  .jr-sum .k { color:#8b949e; font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:.3px; }
  .jr-sum .v { color:#e6edf3; font-size:19px; font-weight:800; font-family:ui-monospace,Consolas,monospace; }
  .jr-sum .v.up { color:#3fb950 !important; } .jr-sum .v.down { color:#f85149 !important; }
  .jr-sum .s { color:#6b7686; font-size:10.5px; }

  /* Tabla de operaciones (calco de table.pos de Inicio) */
  table.jpos { width:100%; border-collapse:collapse; font-size:13px; }
  table.jpos th { color:#8b949e; text-align:left; font-weight:600; font-size:11.5px;
      padding:11px 16px; border-bottom:1px solid #1b2430; text-transform:uppercase; letter-spacing:.3px; }
  table.jpos td { color:#e6edf3; padding:11px 16px; border-bottom:1px solid #141a22; }
  table.jpos tr:last-child td { border-bottom:none; }
  table.jpos tbody tr { transition:background .12s ease; }
  table.jpos tbody tr:hover { background:#131b27; }
  table.jpos .r { text-align:right; font-family:ui-monospace,Consolas,monospace; }
  .jpos-sym { display:flex; align-items:center; gap:10px; font-weight:700; white-space:nowrap; }
  .jpos-side { font-size:11px; font-weight:700; padding:3px 10px; border-radius:999px; }
  .jpos-side.buy { background:rgba(63,185,80,.12); color:#3fb950; }
  .jpos-side.sell { background:rgba(248,81,73,.12); color:#f85149; }
  .jpos-fch { color:#8b949e; font-family:ui-monospace,Consolas,monospace; }
  .jpos-estr { color:#8b949e; }
  td.up { color:#3fb950 !important; font-weight:700; }
  td.down { color:#f85149 !important; font-weight:700; }
  .jpos-res { font-weight:800; padding:3px 10px; border-radius:7px; font-family:ui-monospace,Consolas,monospace; }
  .jpos-res.up { background:rgba(63,185,80,.12); color:#3fb950; }
  .jpos-res.down { background:rgba(248,81,73,.12); color:#f85149; }
  .jr-empty { display:flex; flex-direction:column; align-items:center; gap:6px; padding:30px 10px;
      color:#8b949e; font-size:13px; text-align:center; }

  /* Ficha */
  .jr-ophead { display:flex; align-items:center; gap:12px; flex-wrap:wrap; margin:6px 0 12px;
      padding:12px 14px; background:#0d131d; border:1px solid #1b2430; border-radius:12px; }
  .jr-ophead .sym { display:flex; align-items:center; gap:10px; font-size:16px; font-weight:800; color:#fff; }
  .jr-ophead .meta { color:#8b949e; font-size:12.5px; font-family:ui-monospace,Consolas,monospace; }
  .jr-ophead .res { margin-left:auto; font-size:18px; font-weight:800; font-family:ui-monospace,Consolas,monospace; }
  .jr-ophead .res.up { color:#3fb950; } .jr-ophead .res.down { color:#f85149; }
  .jr-rr { display:flex; gap:22px; flex-wrap:wrap; color:#8b949e; font-size:12.5px; margin:10px 2px 6px; }
  .jr-rr b { color:#e6edf3; font-family:ui-monospace,Consolas,monospace; }
  .jr-rr b.up { color:#3fb950; } .jr-rr b.down { color:#f85149; }
  .jr-chart { background:#0b1017; border:1px solid #1b2430; border-radius:12px; padding:6px 8px; }
  .jr-note { color:#6b7686; font-size:11px; margin-top:8px; line-height:1.5; }
  .jr-ok { color:#3fb950; font-size:13px; font-weight:600; margin-top:6px; }
</style>
"""

_ESTRATEGIAS = ["—", "Breakout", "Pullback", "Tendencia", "Rango",
                "Soporte/Resistencia", "Noticia", "Scalping", "Otra"]
_EMOCIONES = ["—", "Confianza", "Calma", "Duda", "FOMO", "Miedo",
              "Avaricia", "Impaciencia", "Revancha"]


def _dur(seg):
    seg = int(seg or 0)
    d, seg = divmod(seg, 86400)
    h, seg = divmod(seg, 3600)
    mn = seg // 60
    if d:
        return f"{d}d {h}h"
    if h:
        return f"{h}h {mn}m"
    return f"{mn}m"


def _pf(x):
    return "∞" if x == float("inf") else f"{x:,.2f}"


def _tabla_y_metricas(m, ops, stt):
    st.html("<div class='jr-sec'><h3>Diario de operaciones</h3>"
            "<span class='s'>registro automático desde MetaTrader 5</span></div>")
    with st.container(key="jr_card"):
        if stt["n"] == 0:
            st.html("<div class='jr-empty'><span class='jrmi' style='font-size:30px'>history</span>"
                    "Todavía no hay operaciones cerradas.<br>"
                    "Cada operación que cierres quedará registrada aquí automáticamente.</div>")
            return

        wr = stt["win_rate"]
        pf = stt["profit_factor"]
        exp = stt["expectancy"]
        pnl = stt["pnl"]
        rr_sub = (f"R medio {stt['r_medio']:+.2f} · {stt['con_plan']} c/plan"
                  if stt.get("r_medio") is not None
                  else f"gana {stt['avg_win']:,.0f} / pierde {stt['avg_loss']:,.0f}")
        items = [
            ("Win rate", f"{wr:.1f}%", "up" if wr >= 50 else "down",
             f"{stt['ganadoras']}G / {stt['perdedoras']}P"),
            ("Profit factor", _pf(pf), "up" if pf >= 1 else "down", "ganancias ÷ pérdidas"),
            ("R/R promedio", _pf(stt["rr_prom"]), "", rr_sub),
            ("Expectancy", f"{exp:+,.2f}", "up" if exp >= 0 else "down", f"por operación · {m}"),
            ("Max drawdown", f"-{stt['max_dd']:,.2f}", "down" if stt["max_dd"] else "",
             f"en cerradas · {m}"),
            ("P&amp;L (cerradas)", f"{pnl:+,.2f}", "up" if pnl >= 0 else "down",
             f"{stt['n']} operaciones · {m}"),
        ]
        sum_html = "".join(
            f"<div class='it'><span class='k'>{k}</span>"
            f"<span class='v {cls}'>{v}</span><span class='s'>{s}</span></div>"
            for k, v, cls, s in items)

        filas = ""
        for o in ops[:20]:
            side = "buy" if o["tipo"] == "Compra" else "sell"
            lbl = "BUY" if side == "buy" else "SELL"
            neto = o["neto"]
            ncls = "up" if neto >= 0 else "down"
            fecha = (datetime.fromtimestamp(o["hora_out"]).strftime("%d-%m %H:%M")
                     if o["hora_out"] else "—")
            rr = o.get("rr_real")
            estr = (html.escape(str(o.get("estrategia", "") or ""))
                    or "<span style='color:#424b58'>—</span>")
            filas += (
                "<tr>"
                f"<td class='jpos-fch'>{fecha}</td>"
                f"<td><div class='jpos-sym'>{icono_activo(o['symbol'], 26)}"
                f"{html.escape(str(o['nombre']))}</div></td>"
                f"<td><span class='jpos-side {side}'>{lbl}</span></td>"
                f"<td class='r'>{o['volumen']:,.2f}</td>"
                f"<td class='r'>{o['entrada']:,.5f}</td>"
                f"<td class='r'>{o['salida']:,.5f}</td>"
                f"<td class='r'>{_dur(o['duracion_s'])}</td>"
                f"<td class='r {_updn(rr) if rr is not None else ''}'>"
                f"{'—' if rr is None else f'{rr:+.2f}R'}</td>"
                f"<td class='jpos-estr'>{estr}</td>"
                f"<td class='r'><span class='jpos-res {ncls}'>{neto:+,.2f}</span></td>"
                "</tr>")

        st.html(
            f"<div class='jr-sum'>{sum_html}</div>"
            "<table class='jpos'><thead><tr>"
            "<th>Cierre</th><th>Activo</th><th>Dir.</th><th class='r'>Lotes</th>"
            "<th class='r'>Entrada</th><th class='r'>Salida</th><th class='r'>Duración</th>"
            "<th class='r'>R/R</th><th>Estrategia</th><th class='r'>Resultado</th>"
            f"</tr></thead><tbody>{filas}</tbody></table>"
        )


def _updn(x):
    return "up" if (x or 0) >= 0 else "down"


def _mini_grafico_svg(velas, o):
    """Mini-gráfico de velas de la operación con marcas de entrada/salida y SL/TP,
    etiquetas tipo pill (sin pisarse) y la paleta P&J. Velas: [{t,o,h,l,c}]."""
    if len(velas) < 2:
        return ("<div class='jr-empty'>No hay velas para esta operación "
                "(histórico fuera de rango).</div>")
    niveles = [o["entrada"], o["salida"]]
    if o.get("sl"):
        niveles.append(o["sl"])
    if o.get("tp"):
        niveles.append(o["tp"])
    lo = min(min(v["l"] for v in velas), *niveles)
    hi = max(max(v["h"] for v in velas), *niveles)
    rng = (hi - lo) or 1.0
    W, H, pad = 1000, 270, 16
    padR = 120          # espacio a la derecha para las etiquetas pill
    n = len(velas)
    cw = (W - pad - padR) / n
    def Y(p): return H - pad - (H - 2 * pad) * (p - lo) / rng
    def X(i): return pad + cw * (i + 0.5)

    cuerpo = []
    for i, v in enumerate(velas):
        col = _UP if v["c"] >= v["o"] else _DN
        x = X(i)
        cuerpo.append(f"<line x1='{x:.1f}' y1='{Y(v['h']):.1f}' x2='{x:.1f}' "
                      f"y2='{Y(v['l']):.1f}' stroke='{col}' stroke-width='1'/>")
        y1, y2 = Y(v["o"]), Y(v["c"])
        yt, hgt = min(y1, y2), max(1.0, abs(y1 - y2))
        bw = max(1.8, cw * 0.62)
        cuerpo.append(f"<rect x='{x-bw/2:.1f}' y='{yt:.1f}' width='{bw:.1f}' "
                      f"height='{hgt:.1f}' rx='1' fill='{col}'/>")

    def idx(ts):
        return min(range(n), key=lambda i: abs(velas[i]["t"] - ts))

    # Niveles con etiqueta pill a la derecha; se reparten en Y para no pisarse.
    lines = []
    etiquetas = []   # (y_real, color, texto)
    lines.append((Y(o["entrada"]), _AZ, f"Entrada {o['entrada']:,.5f}", False))
    lines.append((Y(o["salida"]), _TX, f"Salida {o['salida']:,.5f}", False))
    if o.get("sl"):
        lines.append((Y(o["sl"]), _DN, f"SL {o['sl']:,.5f}", True))
    if o.get("tp"):
        lines.append((Y(o["tp"]), _UP, f"TP {o['tp']:,.5f}", True))

    svg = list(cuerpo)
    # Dibujar las líneas horizontales (hasta donde empiezan las pills).
    xL = W - padR
    for y, col, txt, dash in lines:
        d = "stroke-dasharray='5 4'" if dash else ""
        svg.append(f"<line x1='{pad}' y1='{y:.1f}' x2='{xL:.1f}' y2='{y:.1f}' "
                   f"stroke='{col}' stroke-width='1.3' {d} opacity='.85'/>")

    # Repartir las pills en Y (anti-solape): ordenar por y y separar >= 20px.
    pills = sorted([(y, col, txt) for (y, col, txt, _d) in lines], key=lambda t: t[0])
    PH = 19
    for i in range(1, len(pills)):
        if pills[i][0] - pills[i - 1][0] < PH:
            pills[i] = (pills[i - 1][0] + PH, pills[i][1], pills[i][2])
    for y, col, txt in pills:
        yy = max(PH / 2 + 2, min(H - PH / 2 - 2, y))
        w = 9 + len(txt) * 5.6
        svg.append(
            f"<rect x='{xL + 6:.1f}' y='{yy - PH/2:.1f}' width='{w:.1f}' height='{PH}' "
            f"rx='5' fill='{col}' fill-opacity='.16' stroke='{col}' stroke-opacity='.6'/>"
            f"<text x='{xL + 6 + w/2:.1f}' y='{yy + 3.5:.1f}' fill='{col}' font-size='10.5' "
            f"font-family='ui-monospace,Consolas,monospace' text-anchor='middle'>{txt}</text>")

    # Puntos de entrada/salida sobre las velas.
    ie, isx = idx(o["hora_in"]), idx(o["hora_out"])
    svg.append(f"<circle cx='{X(ie):.1f}' cy='{Y(o['entrada']):.1f}' r='5' fill='{_AZ}' "
               f"stroke='#0b1017' stroke-width='1.5'/>")
    svg.append(f"<circle cx='{X(isx):.1f}' cy='{Y(o['salida']):.1f}' r='5' fill='{_TX}' "
               f"stroke='#0b1017' stroke-width='1.5'/>")
    return (f"<div class='jr-chart'><svg viewBox='0 0 {W} {H}' width='100%' height='270' "
            f"style='width:100%;height:270px;display:block'>"
            + "".join(svg) + "</svg></div>")


def _ficha(m, ops):
    if not ops:
        return
    opts = {o["pos_id"]: o for o in ops}

    def etiqueta(pid):
        o = opts[pid]
        f = datetime.fromtimestamp(o["hora_out"]).strftime("%d-%m %H:%M") if o["hora_out"] else "—"
        lado = "BUY" if o["tipo"] == "Compra" else "SELL"
        dot = "🟢" if o["neto"] >= 0 else "🔴"
        return f"{dot}  {f}   ·   {o['nombre']} {lado}   ·   {o['neto']:+,.2f} {m}"

    st.html("<div class='jr-sec'><h3>Ficha de la operación</h3>"
            "<span class='s'>captura, estrategia, emoción y R/R</span></div>")
    with st.container(key="jr_ficha"):
        pid = st.selectbox("Operación", list(opts.keys()), format_func=etiqueta,
                           key="jr_sel", label_visibility="collapsed")
        o = opts.get(pid)
        if not o:
            return

        side = "buy" if o["tipo"] == "Compra" else "sell"
        lbl = "BUY" if side == "buy" else "SELL"
        rcls = "up" if o["neto"] >= 0 else "down"
        f_in = datetime.fromtimestamp(o["hora_in"]).strftime("%d-%m %H:%M") if o["hora_in"] else "—"
        f_out = datetime.fromtimestamp(o["hora_out"]).strftime("%d-%m %H:%M") if o["hora_out"] else "—"
        st.html(
            "<div class='jr-ophead'>"
            f"<span class='sym'>{icono_activo(o['symbol'], 30)}{html.escape(str(o['nombre']))}"
            f"<span class='jpos-side {side}'>{lbl}</span></span>"
            f"<span class='meta'>{o['volumen']:,.2f} lotes · {f_in} → {f_out} · "
            f"{_dur(o['duracion_s'])}</span>"
            f"<span class='res {rcls}'>{o['neto']:+,.2f} {m}</span></div>"
        )

        # El mini-gráfico es un SVG grande: st.markdown(unsafe_allow_html) lo respeta
        # mejor que st.html (que puede perder el alto/los nodos del SVG).
        st.markdown(
            _mini_grafico_svg(obtener_velas_rango(o["symbol"], o["hora_in"], o["hora_out"]), o),
            unsafe_allow_html=True)

        rr_plan, rr_real = o.get("rr_plan"), o.get("rr_real")
        plan_txt = (f"R/R planificado <b>{rr_plan:,.2f}</b>" if rr_plan is not None
                    else "R/R planificado <b>—</b> <span style='color:#4b5563'>(abre con SL/TP para registrarlo)</span>")
        real_txt = (f"R realizado <b class='{rcls}'>{rr_real:+.2f}R</b>"
                    if rr_real is not None else "R realizado <b>—</b>")
        st.html(
            f"<div class='jr-rr'><span>{plan_txt}</span><span>{real_txt}</span>"
            f"<span>Comisión <b>{o['comision']:,.2f} {m}</b></span></div>"
        )

        c1, c2 = st.columns(2)
        with c1:
            estr = st.selectbox("Estrategia", _ESTRATEGIAS,
                                index=(_ESTRATEGIAS.index(o["estrategia"])
                                       if o.get("estrategia") in _ESTRATEGIAS else 0),
                                key=f"jr_estr_{pid}")
        with c2:
            emo = st.selectbox("Emoción / estado", _EMOCIONES,
                               index=(_EMOCIONES.index(o["emocion"])
                                      if o.get("emocion") in _EMOCIONES else 0),
                               key=f"jr_emo_{pid}")
        razon = st.text_area("Razón de entrada (opcional)", value=o.get("razon", ""),
                             key=f"jr_raz_{pid}", height=70,
                             placeholder="Por qué entraste, contexto, qué viste…")
        if st.button("Guardar nota", key=f"jr_save_{pid}", type="primary"):
            journal_store.guardar_notas(
                pid, estrategia=("" if estr == "—" else estr),
                emocion=("" if emo == "—" else emo), razon=razon)
            st.session_state["jr_msg"] = True
            st.rerun()
        if st.session_state.pop("jr_msg", None):
            st.html("<div class='jr-ok'>Nota guardada.</div>")


def renderizar_panel_journal(main=None):
    inicializar_mt5()
    st.html(_CSS)
    with st.container(key="jr_wrap"):
        st.html(
            "<div class='jr-head'><div class='ic'><span class='jrmi'>menu_book</span></div>"
            "<div><div class='jr-title'>Diario</div>"
            "<div class='jr-sub'>Trading journal: registro automático, métricas y notas por operación</div>"
            "</div></div>"
        )
        info_c = obtener_info_cuenta()
        m = info_c.get("currency", "USD") if isinstance(info_c, dict) else "USD"
        jd = journal_stats.calcular()
        _tabla_y_metricas(m, jd["operaciones"], jd["stats"])
        _ficha(m, jd["operaciones"])
        st.html(
            "<div class='jr-note'>Operaciones reconstruidas emparejando los deals de "
            "entrada y salida de MetaTrader 5. El R/R planificado aparece en operaciones "
            "abiertas con SL/TP; la captura es un mini-gráfico generado automáticamente.</div>"
        )
