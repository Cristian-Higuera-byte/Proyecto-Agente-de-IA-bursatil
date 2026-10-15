"""Bloques de la vista Resumen: tarjetas KPI, nivel de margen, curva de balance, exposición y nota al pie.
Todos reciben el diccionario `s` de herramientas.estadisticas_portafolio.calcular()."""
import html
import time

import streamlit as st

from componentes_plataforma.resumen.curva import curva_svg
from componentes_plataforma.resumen.datos import PERIODOS
from componentes_plataforma.resumen.formato import compact, vcls as _vcls
from componentes_plataforma.resumen.tarjetas import card


def tarjetas_kpi(s: dict) -> None:
    """Rejilla de 8 tarjetas KPI: capital, P&L, rentabilidad, exposición, riesgo, comisiones y drawdown."""
    m = s["moneda"]
    cap = s["capital"]
    pnl = s["pnl"]
    com = s["comisiones"]
    exp = s["exposicion"]
    rie = s["riesgo"]
    dd = s["drawdown"]
    div = s["dividendos"]
    rent = s["rentabilidad"]
    # ---------- Fila 1 ----------
    d_tot, mes_tot = pnl["dia"]["total"], pnl["mes"]["total"]
    pct = rent["pct"]
    pill = f"<span class='rs-pill {'up' if pct >= 0 else 'down'}'>{pct:+.2f}%</span>"
    # Flotante EN VIVO (feed): mismo dato que el P/G de la barra superior.
    flot_live = ("<span data-pj-acc='profit' data-pj-fmt='signed' "
                 "data-pj-color='1'>{:+,.2f}</span>").format(pnl['dia']['flotante'])
    fila1 = [
        card("cap", "Capital (equity)", f"{cap['equity']:,.2f}", "",
              f"Saldo {cap['balance']:,.2f} · Libre {cap['margen_libre']:,.2f}",
              val_attrs=f"data-pj-acc='equity' data-pj-base='{cap['equity']:.2f}'"),
        card("up" if d_tot >= 0 else "down", "P&amp;L diario",
              compact(d_tot, signo=True), m,
              f"Realizado {pnl['dia']['realizado']:+,.2f} · Flot. {flot_live} "
              f"· {pnl['dia']['cierres']} cierres", arrow=True, valcls=_vcls(d_tot)),
        card("up" if mes_tot >= 0 else "down", "P&amp;L mensual",
              compact(mes_tot, signo=True), m,
              f"Realizado {pnl['mes']['realizado']:+,.2f} · Flot. {flot_live} "
              f"· {pnl['mes']['cierres']} cierres", arrow=True, valcls=_vcls(mes_tot)),
        card("acum", "Rentabilidad acumulada", compact(rent['abs'], signo=True), m,
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
    div_txt = (compact(div['total'], m, signo=True) if abs(div["total"]) > 1e-9
               else "Sin dividendos")
    fila2 = [
        card("exp", "Exposición total", compact(exp['total']), m,
              f"Largos {compact(exp['largos'])} · Cortos {compact(exp['cortos'])} "
              f"· {apal:.1f}× equity", valcls="rs-neu"),
        card("risk", "Riesgo definido", compact(rie['definido'], signo=False), m,
              f"Margen usado {rie['margen_usado']:,.2f} · {sinsl_txt}", valcls="rs-down"),
        card("fee", "Comisiones y swaps", f"{com_tot:,.2f}", m,
              f"Mes {(com['mes'] + com['swap_mes']):,.2f} · Hoy {(com['hoy'] + com['swap_hoy']):,.2f}",
              valcls="rs-down" if com_tot < 0 else "rs-neu"),
        card("dd", dd_lbl, dd_txt, "",
              f"{dd_base} · Div. {div_txt}",
              valcls="rs-down" if dd_pct else "rs-neu"),
    ]
    st.markdown("<div class='rs-grid'>" + "".join(fila1 + fila2) + "</div>",
                unsafe_allow_html=True)


def nivel_margen(s: dict) -> None:
    """Panel con la barra del nivel de margen (semáforo)."""
    rie = s["riesgo"]
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


def curva_balance(s: dict) -> None:
    """Curva de balance con selector de periodo (el selector y la curva forman un solo bloque)."""
    m = s["moneda"]
    # ---------- Curva de balance con selector de periodo (interactivo) ----------
    # El selector y la curva van DENTRO del mismo contenedor (rs_curvapanel)
    # para que se lean como un solo bloque (el selector pertenece al gráfico).
    with st.container(key="rs_curvapanel"):
        periodo = st.segmented_control(
            "Periodo", list(PERIODOS.keys()), default="Todo",
            key="rs_periodo", label_visibility="collapsed")
        dias = PERIODOS.get(periodo or "Todo")
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
            + curva_svg(curva, m),
            unsafe_allow_html=True,
        )


def exposicion_por_activo(s: dict) -> None:
    """Tabla de exposición por activo."""
    m = s["moneda"]
    exp = s["exposicion"]
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
                f"<td>{compact(r['notional'], m)}</td>"
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


def nota_pie(s: dict) -> None:
    """Nota al pie sobre el drawdown, los dividendos y el origen de los datos."""
    dd = s["drawdown"]
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
