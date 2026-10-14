"""Posiciones abiertas de Inicio (precio y P/G en vivo por el feed)."""
import streamlit as st

from components.iconos import icono_activo
from components.inicio.formato import mi
from tools.mt5_bridge import obtener_posiciones


def dibujar_posiciones():
    pos = obtener_posiciones()
    s1, s2 = st.columns([4, 1], vertical_alignment="center")
    with s1:
        st.html(f"<div class='ini-sec'><h3>Posiciones abiertas</h3>"
                f"<span class='s'>{len(pos)} {'posición' if len(pos) == 1 else 'posiciones'}</span></div>")
    with s2:
        if st.button("Ver cartera", key="ini_vercartera", icon=":material/arrow_forward:",
                     width="stretch"):
            st.session_state.nav_activo = "portafolio"
            st.rerun()
    with st.container(key="ini_cartera"):
        if not pos:
            st.html("<div class='pos-empty'>" + mi("inventory_2") +
                    "No tienes posiciones abiertas.<br>Las operaciones que abras aparecerán aquí.</div>")
            return
        filas = ""
        for p in pos:
            neto = p["profit"] + p.get("swap", 0.0)     # igual que Cartera y la barra superior
            tk = p.get("ticket")
            compra = p["tipo"] == "Compra"
            sym = p["symbol"].replace("...", "")
            filas += (
                "<tr>"
                f"<td><div class='pos-sym'>{icono_activo(p['symbol'], 26)}{sym}</div></td>"
                f"<td><span class='pos-side {'buy' if compra else 'sell'}'>{p['tipo']}</span></td>"
                f"<td class='r'>{p['volumen']:,.2f}</td>"
                f"<td class='r'>{p['precio_apertura']:,.5f}</td>"
                f"<td class='r' data-pj-posc='{tk}' data-pj-d='5'>{p['precio_actual']:,.5f}</td>"
                f"<td class='r {'car-up' if neto >= 0 else 'car-down'}' data-pj-pos='{tk}'>{neto:+,.2f}</td>"
                "</tr>"
            )
        st.html(
            "<table class='pos'><thead><tr>"
            "<th>Activo</th><th>Tipo</th><th class='r'>Volumen</th>"
            "<th class='r'>Apertura</th><th class='r'>Actual</th><th class='r'>P/G</th>"
            "</tr></thead><tbody>" + filas + "</tbody></table>"
        )
