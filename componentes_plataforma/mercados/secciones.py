"""Secciones de la página Mercados: "Pulso del mercado" (tarjetas) y tabla por categoría."""
import streamlit as st

from componentes_plataforma.mercados.broker import fila, items, resolver
from componentes_plataforma.mercados.constantes import CATALOGO, ORDENES, RESUMEN
from componentes_plataforma.mercados.piezas import fila_html, tarjeta_html


def abrir_ficha(real: str, nombre: str, cat: str):
    st.session_state.mkt_detalle = {"sym": real, "label": nombre, "cat": cat}
    st.rerun()


def resumen():
    filas = []
    for cat, idx, tag in RESUMEN:
        cands, nombre = CATALOGO[cat][idx]
        real = resolver(cands)
        f = fila(real, nombre) if real else None
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
                st.html(tarjeta_html(f, tag))
                if st.button("ver", key=f"mktclk_card_{f['sym']}"):
                    abrir_ficha(f["sym"], f["label"], cat)


def render_tabla(categoria: str):
    filas = [f for f in (fila(r, n) for r, n, _ in items(categoria)) if f]
    total = len(filas)

    q = (st.session_state.get("mkt_q") or "").strip().lower()
    if q:
        filas = [f for f in filas if q in f["label"].lower() or q in f["sym"].lower()
                 or q in f["desc"].lower()]
    orden = st.session_state.get("mkt_orden") or ORDENES[0]
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
                st.html(fila_html(f))
                if st.button("ver", key=f"mktclk_{f['sym']}"):
                    abrir_ficha(f["sym"], f["label"], categoria)
    return total, len(filas)
