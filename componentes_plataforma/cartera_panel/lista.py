"""
cartera_panel/lista.py
----------------------
Lista de CARTERA (posiciones abiertas) que reemplaza al watchlist en la vista de
Trading cuando el usuario entra a "Cartera". Misma estética que la watchlist; cada fila
es clicable y carga ese símbolo en el gráfico central. Incluye la detección de cierres
(posiciones que desaparecen → tarjeta "cerrada" con su P/G) y, al desplegar una fila, el
detalle inline (detalle.py). Los datos salen en vivo de MT5.
"""
import html
import re
import time

import streamlit as st

from herramientas.puente_mt5 import obtener_posiciones, obtener_historial
from herramientas import gestor_lista_activos as wl
from herramientas import almacen_cerradas

from componentes_plataforma.iconos import icono_activo   # íconos estilo XM (comunes a todo el dashboard)

from .comun import neto, fmtp, css_lista, css_detalle
from .detalle import detalle_inline

ALTURA_LISTA = 700


def _detectar_cierres(pos: list):
    """Compara las posiciones actuales con la foto anterior: las que ya no están
    se cerraron (manual o automáticamente) → se registran como tarjetas cerradas.
    Guarda anti-fallo: si TODO desaparece de golpe (y había más de una), se asume
    un fallo momentáneo de MT5, no cierres reales."""
    prev = st.session_state.get("ca_prev", {})
    actuales = {p.get("ticket") for p in pos}
    reales = st.session_state.setdefault("ca_pg_real", {})   # P/G exacto de cierres manuales
    desaparecidos = [(tk, info) for tk, info in prev.items() if tk not in actuales]
    if desaparecidos and not (not pos and len(prev) > 1):
        try:
            hist = obtener_historial(dias=1, limite=80)   # P/G y precio de cierre reales
        except Exception:
            hist = []
        nuevas = []
        for tk, info in desaparecidos:
            if tk in reales:                               # cierre manual: P/G exacto
                pg, cierre = reales.pop(tk), info.get("ac")
            else:                                          # cierre automático: confirmar en historial
                h = next((x for x in hist if x.get("symbol") == info.get("real")
                          and abs(float(x.get("volumen", 0)) - float(info.get("volumen", 0))) < 1e-6), None)
                if h is None:
                    continue                               # no confirmado (posible fallo de MT5): no inventar tarjeta
                pg, cierre = h.get("pg"), h.get("precio_cierre")
            nuevas.append({**info, "ticket": tk, "pg": pg, "cierre": cierre, "hora": time.strftime("%H:%M")})
        if nuevas:
            cerr = {c["ticket"] for c in nuevas}
            st.session_state.ca_cerradas = (nuevas + st.session_state.get("ca_cerradas", []))[:8]
            almacen_cerradas.guardar(st.session_state.ca_cerradas)   # sobrevive al F5
            if st.session_state.get("ca_detalle") in cerr:
                st.session_state.ca_detalle = None   # cierra el detalle de la que se cerró
    # Foto actual para la próxima comparación.
    st.session_state.ca_prev = {
        p.get("ticket"): {"sym": wl.nombre_visible(p["symbol"]), "real": p["symbol"],
                          "side": p.get("tipo", ""), "volumen": p.get("volumen", 0),
                          "ap": float(p.get("precio_apertura", 0) or 0),
                          "ac": float(p.get("precio_actual", 0) or 0), "pg": neto(p)}
        for p in pos}


def _render_cerradas():
    """Tarjetas de posiciones cerradas (manual o auto), con detalle y 'Aceptar'."""
    cerradas = st.session_state.get("ca_cerradas", [])
    for c in cerradas:
        tk = c["ticket"]
        side = "buy" if c.get("side") == "Compra" else "sell"
        side_lbl = "BUY" if side == "buy" else "SELL"
        pg = float(c.get("pg", 0.0) or 0.0)
        cls_pl = "ca-up" if pg >= 0 else "ca-down"
        with st.container(key=f"cacerr_{tk}"):
            st.markdown(
                "<div class='ca-closed'>"
                "<div class='cc-top'>"
                f"<span class='cc-ico'>{icono_activo(c.get('real', ''), 30)}</span>"
                f"<span class='cc-sym'>{html.escape(str(c.get('sym', '')))}"
                f"<span class='cc-badge {side}'>{side_lbl}</span>"
                "<span class='cc-tag'>CERRADA</span></span>"
                f"<span class='cc-pl {cls_pl}'>{pg:+,.2f}</span></div>"
                "<div class='cc-grid'>"
                f"<span class='it'>Cantidad <b>{c.get('volumen', 0):,.2f}</b></span>"
                f"<span class='it'>Apertura <b>{fmtp(c.get('ap'))}</b></span>"
                f"<span class='it'>Cierre <b>{fmtp(c.get('cierre', c.get('ac')))}</b></span>"
                f"<span class='it'>Hora <b>{c.get('hora', '')}</b></span>"
                "</div></div>",
                unsafe_allow_html=True,
            )
            if st.button("Aceptar", key=f"cacerr_ok_{tk}", width="stretch"):
                st.session_state.ca_cerradas = [x for x in cerradas if x["ticket"] != tk]
                almacen_cerradas.guardar(st.session_state.ca_cerradas)
                st.rerun()


def renderizar_cartera_lista():
    """Panel de posiciones abiertas (reemplaza al watchlist en 'Cartera')."""
    css_lista()
    css_detalle()
    pos = obtener_posiciones()
    st.session_state.ca_editando = False   # lo activan los editores si abren un input
    # Tras un F5 la sesión es nueva: recuperar las tarjetas cerradas del archivo.
    if "ca_cerradas" not in st.session_state:
        st.session_state.ca_cerradas = almacen_cerradas.leer()
    _detectar_cierres(pos)                 # registra tarjetas de posiciones cerradas

    with st.container(key="ca_panel"):
        st.markdown(
            "<div class='ca-head'>"
            "<div class='ic'><span class='ca-mi'>account_balance_wallet</span></div>"
            "<div><div class='ca-title'>Cartera</div>"
            "<div class='ca-sub'>Posiciones abiertas en tiempo real</div></div></div>",
            unsafe_allow_html=True,
        )

        # P/G NETO (profit + swap): así el total coincide con el P/G de la cuenta
        # que se muestra junto al saldo (account_info.profit incluye el swap).
        total = sum(neto(p) for p in pos) if pos else 0.0
        cls_t = "ca-up" if total >= 0 else "ca-down"
        # data-pj-acc="profit": el feed en vivo lo pinta con el MISMO dato que la
        # barra superior → ambos van siempre a la par.
        st.markdown(
            f"<div class='ca-totals'><div><span class='lbl'>P/G total</span>"
            f"<span class='cnt'>{len(pos)}</span></div>"
            f"<span class='val {cls_t}' data-pj-acc='profit' data-pj-zero='1' "
            f"data-pj-up='#2ebd85' data-pj-dn='#f6465d'>{total:+,.2f}</span></div>",
            unsafe_allow_html=True,
        )

        # Mensaje de error puntual (p. ej. "no se pudo cerrar").
        r = st.session_state.get("ca_result")
        if r:
            cls_r = "ca-result-ok" if r[0] == "ok" else "ca-result-err"
            st.markdown(f"<div class='{cls_r}'>{html.escape(r[1])}</div>", unsafe_allow_html=True)

        hay_cerradas = bool(st.session_state.get("ca_cerradas"))
        if not pos and not hay_cerradas:
            st.markdown(
                "<div class='ca-empty'>Nada que mostrar.<br>"
                "Las operaciones que abras aparecerán aquí.</div>",
                unsafe_allow_html=True,
            )
            return

        abierta = st.session_state.get("ca_detalle")   # ticket de la fila desplegada
        with st.container(height=ALTURA_LISTA, border=False, key="ca_scroll"):
            # Tarjetas de posiciones cerradas (manual o auto) con "Aceptar", dentro
            # del scroll para que compartan el mismo inset que las abiertas.
            _render_cerradas()
            if not pos:
                st.markdown("<div class='ca-empty' style='padding:24px 10px;'>"
                            "No tienes posiciones abiertas.</div>", unsafe_allow_html=True)
            for i, p in enumerate(pos):
                sym = p["symbol"]
                base = wl.nombre_visible(sym)
                slug = re.sub(r"\W", "", sym) + f"_{i}"
                tk = p.get("ticket")
                es_sel = (abierta == tk)
                cls_sel = " sel" if es_sel else ""
                lado = p.get("tipo", "")
                side = "buy" if lado == "Compra" else "sell"
                side_lbl = "BUY" if lado == "Compra" else "SELL"
                prof = neto(p)
                cls_pl = "ca-up" if prof >= 0 else "ca-down"
                caret = "▴" if es_sel else "▾"

                with st.container(key=f"carow_{slug}"):
                    st.markdown(
                        f"<div class='ca-row {side}{cls_sel}'>"
                        f"<span class='ca-ico'>{icono_activo(sym, 36)}</span>"
                        f"<div class='ca-mid'>"
                        f"<div class='ca-tk'>{html.escape(base)}"
                        f"<span class='ca-badge {side}'>{side_lbl}</span></div>"
                        f"<div class='ca-meta'>{p.get('volumen',0):,.2f} lotes · "
                        f"{p.get('precio_apertura',0):,.5f}</div></div>"
                        f"<div class='ca-right'>"
                        f"<div class='ca-pl {cls_pl}' data-pj-pos='{tk}' "
                        f"data-pj-up='#2ebd85' data-pj-dn='#f6465d'>{prof:+,.2f}</div>"
                        f"<span class='ca-caret'>{caret}</span></div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    # Clic en la fila -> despliega/pliega el detalle inline (acordeón, como XM).
                    # Rerun de FRAGMENTO (no de app): así el gráfico de col_center NO se
                    # refresca al abrir/cerrar una posición en la lista.
                    if st.button("ver", key=f"casel_{slug}"):
                        st.session_state.ca_detalle = None if es_sel else tk
                        st.session_state.pop("ca_result", None)
                        st.rerun(scope="fragment")
                    # X -> abre el modal de confirmación de cierre
                    if st.button("✕", key=f"cacls_{slug}", help="Cerrar posición"):
                        st.session_state.ca_cerrar = {
                            "ticket": tk, "symbol": base, "profit": prof,
                            "tipo": lado, "volumen": p.get("volumen", 0),
                        }
                        st.session_state.pop("ca_result", None)
                        st.rerun(scope="app")

                # Detalle desplegable justo debajo de la fila (como XM)
                if es_sel:
                    detalle_inline(tk, p)
