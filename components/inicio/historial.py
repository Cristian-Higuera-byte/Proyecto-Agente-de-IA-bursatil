"""Historial de operaciones cerradas de Inicio, con "Ver más / Ver menos" (de a 10 hacia abajo)."""
import datetime as _dt

import streamlit as st

from components.iconos import icono_activo
from components.inicio.formato import mi
from tools.mt5_bridge import obtener_historial


def dibujar_historial():
    hist = obtener_historial()
    st.html("<div class='ini-sec'><h3>Historial</h3>"
            f"<span class='s'>{len(hist)} "
            f"{'operación cerrada' if len(hist) == 1 else 'operaciones cerradas'}</span></div>")
    with st.container(key="ini_hist"):
        if not hist:
            st.html("<div class='pos-empty'>" + mi("history") +
                    "No hay operaciones cerradas.<br>"
                    "Aquí verás las compras y ventas que cierres.</div>")
            return
        total = sum(h["pg"] for h in hist)
        ganadoras = sum(1 for h in hist if h["pg"] > 0)
        pct = ganadoras / len(hist) * 100
        st.html(
            "<div class='hist-sum'>"
            "<div class='it'><span class='k'>P/G realizado</span>"
            f"<span class='v {'car-up' if total >= 0 else 'car-down'}'>{total:+,.2f}</span></div>"
            "<div class='it'><span class='k'>Operaciones</span>"
            f"<span class='v'>{len(hist)}</span></div>"
            "<div class='it'><span class='k'>Ganadoras</span>"
            f"<span class='v'>{ganadoras}/{len(hist)} · {pct:.0f}%</span></div>"
            "</div>"
        )
        n = st.session_state.get("ini_hist_n", 10)
        filas = ""
        for h in hist[:n]:
            compra = h["tipo"] == "Compra"
            sym = h["symbol"].replace("...", "")
            fch = _dt.datetime.fromtimestamp(h["fecha"]).strftime("%d-%m %H:%M")
            filas += (
                "<tr>"
                f"<td class='hist-fch'>{fch}</td>"
                f"<td><div class='pos-sym'>{icono_activo(h['symbol'], 26)}{sym}</div></td>"
                f"<td><span class='pos-side {'buy' if compra else 'sell'}'>{h['tipo']}</span></td>"
                f"<td class='r'>{h['volumen']:,.2f}</td>"
                f"<td class='r'>{h['precio_cierre']:,.5f}</td>"
                f"<td class='r {'car-up' if h['pg'] >= 0 else 'car-down'}'>{h['pg']:+,.2f}</td>"
                "</tr>"
            )
        st.html(
            "<table class='pos'><thead><tr>"
            "<th>Fecha</th><th>Activo</th><th>Tipo</th><th class='r'>Volumen</th>"
            "<th class='r'>Cierre</th><th class='r'>P/G</th>"
            "</tr></thead><tbody>" + filas + "</tbody></table>"
        )
    # Ver más / Ver menos (despliegan de a 10 hacia abajo, dentro de Inicio)
    n = st.session_state.get("ini_hist_n", 10)
    if len(hist) > 10:
        restantes = len(hist) - n
        c1, c2, _ = st.columns([1, 1, 3])
        if restantes > 0:
            with c1:
                if st.button(f"Ver más ({restantes})", key="ini_vermas",
                             icon=":material/expand_more:", width="stretch"):
                    st.session_state.ini_hist_n = n + 10
                    st.rerun(scope="fragment")
        if n > 10:
            with c2:
                if st.button("Ver menos", key="ini_vermenos",
                             icon=":material/expand_less:", width="stretch"):
                    st.session_state.ini_hist_n = 10
                    st.rerun(scope="fragment")
