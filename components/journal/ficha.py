"""Ficha de la operación: cabecera, mini-gráfico, R/R y notas editables (estrategia, emoción, razón)."""
import html
from datetime import datetime

import streamlit as st

from components.iconos import icono_activo
from components.journal.datos import EMOCIONES, ESTRATEGIAS
from components.journal.formato import dur
from components.journal.mini_grafico import mini_grafico_svg
from tools import journal_store
from tools.mt5_bridge import obtener_velas_rango


def ficha(m, ops):
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
            f"{dur(o['duracion_s'])}</span>"
            f"<span class='res {rcls}'>{o['neto']:+,.2f} {m}</span></div>"
        )

        # El mini-gráfico es un SVG grande: st.markdown(unsafe_allow_html) lo respeta
        # mejor que st.html (que puede perder el alto/los nodos del SVG).
        st.markdown(
            mini_grafico_svg(obtener_velas_rango(o["symbol"], o["hora_in"], o["hora_out"]), o),
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
            estr = st.selectbox("Estrategia", ESTRATEGIAS,
                                index=(ESTRATEGIAS.index(o["estrategia"])
                                       if o.get("estrategia") in ESTRATEGIAS else 0),
                                key=f"jr_estr_{pid}")
        with c2:
            emo = st.selectbox("Emoción / estado", EMOCIONES,
                               index=(EMOCIONES.index(o["emocion"])
                                      if o.get("emocion") in EMOCIONES else 0),
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
