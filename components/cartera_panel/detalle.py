"""
cartera_panel/detalle.py
------------------------
Detalle desplegable de una posición (acordeón inline bajo su fila, como XM): al tocar
una posición se despliega toda la info, el botón de cierre, "Mostrar gráfico" y los
editores de Take Profit / Stop Loss y Stop dinámico (trailing). El P/G y el precio
actual se pintan en vivo por el feed; mientras una fila está desplegada, app.py pausa el
auto-refresco del fragmento (ca_editando).
"""
import html
import time
from datetime import datetime

import streamlit as st

from tools.mt5_bridge import modificar_sltp, especs_posicion
from tools import trailing_store
from tools import watchlist_manager as wl

from .comun import neto


def _resolver_nivel(clave, modo, valor, e, ap, ac, compra):
    """Devuelve (precio, error). clave='tp'|'sl'; modo='Precio'|'Cantidad'.
    'Cantidad' convierte un objetivo en dinero a precio usando k (valor de 1
    unidad de precio por lote) desde el precio de apertura. Valida lado y la
    distancia mínima del bróker respecto del precio actual."""
    valor = (valor or "").strip().replace(",", "")
    if not valor:
        return None, None
    try:
        x = float(valor)
    except ValueError:
        return None, "Ingresa un número."
    dig = e.get("digitos", 5)
    k = e.get("k", 0.0)
    vol = e.get("volumen", 0.0) or 1.0
    if (modo or "Precio") == "Cantidad":
        if k <= 0 or vol <= 0:
            return None, "No se puede convertir el monto a precio."
        mov = abs(x) / (k * vol)
        if clave == "tp":
            precio = ap + mov if compra else ap - mov          # objetivo favorable
        else:
            precio = ap - mov if compra else ap + mov          # pérdida tolerada
    else:
        precio = x
    precio = round(precio, dig)
    dist = e.get("stops_level", 0) * e.get("point", 0.0)
    if clave == "tp":
        if compra and precio <= ac + dist:
            return None, f"El take profit debe estar sobre {ac + dist:,.{dig}f}."
        if (not compra) and precio >= ac - dist:
            return None, f"El take profit debe estar bajo {ac - dist:,.{dig}f}."
    else:
        if compra and precio >= ac - dist:
            return None, f"El stop loss debe estar bajo {ac - dist:,.{dig}f}."
        if (not compra) and precio <= ac + dist:
            return None, f"El stop loss debe estar sobre {ac + dist:,.{dig}f}."
    return precio, None


def _editor_nivel(clave, titulo, ticket, p, e, ap, ac, compra, bloqueado=False):
    """Toggle Take profit / Stop loss con el editor desplegable (Precio/Cantidad,
    input, Cancelar/Guardar), igual que XM. Aplica con modificar_sltp.
    `bloqueado`: el nivel lo gestiona el stop dinámico → se muestra en gris, sin editar."""
    existe = float(p.get(clave, 0.0) or 0.0)
    dig = e.get("digitos", 5)
    if bloqueado:
        st.toggle(titulo, value=True, key=f"cad_{clave}_blk_{ticket}", disabled=True)
        st.markdown("<div class='cad-note'>Gestionado por el stop dinámico. Para cambiarlo, "
                    "edita la distancia o quita el stop dinámico.</div>", unsafe_allow_html=True)
        return
    on = st.toggle(titulo, value=existe > 0, key=f"cad_{clave}_on_{ticket}")
    if not on:
        if existe > 0:
            if st.button(f"Quitar {titulo.lower()}", key=f"cad_{clave}_quitar_{ticket}",
                         width="stretch"):
                res = modificar_sltp(ticket, **{clave: 0.0})
                _fb_sltp(res, titulo, "quitado")
                st.rerun(scope="fragment")
        return
    st.session_state.ca_editando = True   # hay un input abierto: pausa el auto-refresco
    modo = st.segmented_control(
        "modo", ["Precio", "Cantidad"], default="Precio",
        key=f"cad_{clave}_modo_{ticket}", label_visibility="collapsed")
    st.markdown("<div class='cad-note'>Las cantidades finales pueden diferir de los "
                "valores introducidos.</div>", unsafe_allow_html=True)
    ph = f"Nivel de {titulo.lower()}"
    pre = f"{existe:.{dig}f}" if (existe > 0 and (modo or "Precio") == "Precio") else ""
    valor = st.text_input(ph, value=pre, placeholder=ph,
                          key=f"cad_{clave}_val_{ticket}", label_visibility="collapsed")
    precio, err = _resolver_nivel(clave, modo, valor, e, ap, ac, compra)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Cancelar", key=f"cad_{clave}_cancelar_{ticket}", width="stretch"):
            st.session_state[f"cad_{clave}_on_{ticket}"] = False
            st.rerun(scope="fragment")
    with c2:
        if st.button("Guardar", key=f"cad_{clave}_guardar_{ticket}", width="stretch",
                     type="primary", disabled=(precio is None)):
            res = modificar_sltp(ticket, **{clave: precio})
            _fb_sltp(res, titulo, "guardado")
            st.rerun(scope="fragment")
    if valor and err:
        st.markdown(f"<div class='cad-err'>{html.escape(err)}</div>", unsafe_allow_html=True)


def _fb_sltp(res, titulo, verbo):
    if isinstance(res, dict) and "error" in res:
        st.session_state.cad_fb = ("err", f"No se pudo guardar: {res['error']}")
    else:
        st.session_state.cad_fb = ("ok", f"{titulo} {verbo}.")


def _resolver_distancia(valor, sm, dig):
    """Valida la distancia (en precio) del Stop dinámico: número > 0 y no menor
    que la distancia mínima del bróker (stops_level × point)."""
    valor = (valor or "").strip().replace(",", "")
    if not valor:
        return None, None
    try:
        x = float(valor)
    except ValueError:
        return None, "Ingresa un número."
    if x <= 0:
        return None, "La distancia debe ser mayor que cero."
    x = round(x, dig)
    if sm > 0 and x < sm:
        return None, f"La distancia mínima del bróker es {sm:,.{dig}f}."
    return x, None


def _editor_trailing(ticket, p, e):
    """Toggle 'Stop dinámico (trailing)': el SL sigue al precio a una distancia
    fija cuando la operación va a favor y nunca retrocede. La config se guarda en
    data/trailing.json; el motor de servidor_datos.py la aplica en vivo (por eso
    requiere ese proceso encendido).

    Estados: activado sin guardar -> formulario; ya guardado -> resumen + Editar;
    toggle apagado con config -> botón Quitar."""
    cfg = trailing_store.leer().get(int(ticket))
    dig = e.get("digitos", 5)
    sm = e.get("stops_level", 0) * e.get("point", 0.0)
    edit_key = f"cad_trail_edit_{ticket}"

    on = st.toggle("Stop dinámico (trailing)", value=cfg is not None, key=f"cad_trail_on_{ticket}")
    if not on:
        if cfg is not None:
            if st.button("Quitar stop dinámico", key=f"cad_trail_quitar_{ticket}", width="stretch"):
                trailing_store.quitar(ticket)
                # El stop dinámico ERA el stop: al quitarlo se quita también el SL que
                # el motor había puesto (si no, el "Stop loss" manual quedaría activo solo).
                modificar_sltp(ticket, sl=0.0)
                st.session_state.pop(edit_key, None)
                st.session_state.cad_fb = ("ok", "Stop dinámico quitado.")
                st.rerun()
        return

    # Estado GUARDADO (hay config y no se está editando): resumen + "Editar".
    if cfg is not None and not st.session_state.get(edit_key, False):
        st.markdown(
            "<div class='cad-trail-on'>"
            "<span class='k'>Stop dinámico activo</span>"
            f"<span class='v'>Distancia {cfg['dist']:,.{dig}f}</span></div>"
            "<div class='cad-note'>El stop loss sigue al precio y solo se mueve a tu favor. "
            "Requiere el servidor de datos encendido.</div>",
            unsafe_allow_html=True,
        )
        if st.button("Editar distancia", key=f"cad_trail_editar_{ticket}", width="stretch"):
            st.session_state[edit_key] = True
            st.rerun()
        return

    # Estado FORMULARIO (recién activado o editando). Hay un input: se pausa el
    # auto-refresco de la lista para no perder el foco mientras se escribe.
    st.session_state.ca_editando = True
    st.markdown("<div class='cad-note'>El stop loss seguirá al precio a la distancia indicada y "
                "solo se moverá a tu favor. Requiere el servidor de datos encendido.</div>",
                unsafe_allow_html=True)
    pre = f"{cfg['dist']:.{dig}f}" if cfg else ""
    ph = "Distancia (en precio)"
    valor = st.text_input(ph, value=pre, placeholder=ph, key=f"cad_trail_val_{ticket}",
                          label_visibility="collapsed")
    dist, err = _resolver_distancia(valor, sm, dig)
    if sm > 0:
        st.markdown(f"<div class='cad-note'>Distancia mínima del bróker: {sm:,.{dig}f}.</div>",
                    unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Cancelar", key=f"cad_trail_cancelar_{ticket}", width="stretch"):
            if cfg is not None:
                st.session_state[edit_key] = False       # vuelve al resumen
            else:
                st.session_state[f"cad_trail_on_{ticket}"] = False   # apaga el toggle
            st.rerun()
    with c2:
        if st.button("Guardar", key=f"cad_trail_guardar_{ticket}", width="stretch",
                     type="primary", disabled=(dist is None)):
            trailing_store.fijar(ticket, dist)
            st.session_state[edit_key] = False
            st.session_state.cad_fb = ("ok", "Stop dinámico activado.")
            st.rerun()
    if valor and err:
        st.markdown(f"<div class='cad-err'>{html.escape(err)}</div>", unsafe_allow_html=True)


def detalle_inline(ticket, p):
    """Detalle de la posición desplegado inline, justo bajo su fila (acordeón, XM).
    `p` llega fresco de obtener_posiciones() desde el bucle de la lista."""
    with st.container(key=f"cadet_wrap_{ticket}"):
        if not p:
            st.markdown("<div class='cad-empty'>La posición ya no está abierta.</div>",
                        unsafe_allow_html=True)
            return
        e = especs_posicion(ticket) or {}
        sym = p["symbol"]
        base = wl.nombre_visible(sym)
        lado = p.get("tipo", "")
        compra = (lado == "Compra")
        neto_pg = neto(p)
        ap = float(p.get("precio_apertura", 0.0) or 0.0)
        ac = float(p.get("precio_actual", 0.0) or 0.0)
        dig = e.get("digitos", 5)
        var = (((ac - ap) if compra else (ap - ac)) / ap * 100.0) if ap else 0.0

        fb = st.session_state.pop("cad_fb", None)
        if fb:
            st.markdown(f"<div class='cad-fb-{'ok' if fb[0]=='ok' else 'err'}'>"
                        f"{html.escape(fb[1])}</div>", unsafe_allow_html=True)

        # Botón de cierre (texto con el monto en vivo por el feed): abre el MISMO
        # modal de confirmación que la ✕ de la lista (evita cierres accidentales).
        signo = "-" if neto_pg < 0 else ""
        with st.container(key=f"cadet_cerrar_{ticket}"):
            if st.button(f"Cerrar operación: {signo}${abs(neto_pg):,.2f}", key="cadet_btncerrar",
                         type="primary", width="stretch"):
                st.session_state.ca_cerrar = {
                    "ticket": ticket, "symbol": base, "profit": neto_pg,
                    "tipo": lado, "volumen": p.get("volumen", 0),
                }
                st.session_state.pop("ca_result", None)
                st.rerun(scope="app")
        if st.button("Mostrar gráfico", key="cadet_grafico", width="stretch"):
            st.session_state.activo_seleccionado = sym
            # Se mantiene el desplegable abierto (no se limpia ca_detalle).
            st.rerun()

        _grid_y_editores(ticket, p, e, sym, lado, compra, neto_pg, ap, ac, dig, var)


def _grid_y_editores(ticket, p, e, sym, lado, compra, neto_pg, ap, ac, dig, var):
    # Horas: p['tiempo'] es epoch del servidor (XM GMT+3). La local se obtiene
    # restando el desfase (servidor ahora − hora real), redondeado a 15 min.
    tsrv = int(p.get("tiempo", 0) or 0)
    off = e.get("srv_now", 0.0) - time.time() if e.get("srv_now") else 0.0
    off = round(off / 900) * 900
    f_srv = datetime.utcfromtimestamp(tsrv).strftime("%d/%m/%y, %H:%M:%S") if tsrv else "—"
    f_loc = datetime.utcfromtimestamp(max(0, tsrv - off)).strftime("%d/%m/%y, %H:%M:%S") if tsrv else "—"
    tp = float(p.get("tp", 0.0) or 0.0)
    sl = float(p.get("sl", 0.0) or 0.0)
    tp_txt = f"{tp:,.{dig}f}" if tp > 0 else "–"
    sl_txt = f"{sl:,.{dig}f}" if sl > 0 else "–"
    filas = [
        ("ID de orden", str(ticket)),
        ("Instrumento", html.escape(sym)),
        ("Cantidad", f"{p.get('volumen', 0):,.2f} lotes"),
        ("Dirección", html.escape(lado.upper())),
        ("Precio de apertura", f"{ap:,.{dig}f}"),
        ("Precio actual", f"<span data-pj-posc='{ticket}' data-pj-d='{dig}'>{ac:,.{dig}f}</span>"),
        ("PnL", f"<span class='{'cad-up' if neto_pg >= 0 else 'cad-down'}' data-pj-pos='{ticket}' "
                f"data-pj-up='#2ebd85' data-pj-dn='#f6465d'>{neto_pg:+,.2f}</span>"),
        ("Variación del precio", f"{var:+.4f}%"),
        ("Swaps", f"${p.get('swap', 0.0):,.2f}"),
        ("Hora de apertura", f_loc),
        ("Hora apertura (servidor)", f_srv),
        ("Take profit / Stop loss", f"{tp_txt} / {sl_txt}"),
    ]
    st.markdown(
        "<div class='cad-grid'>" + "".join(
            f"<div class='row'><span class='k'>{k}</span><span class='v'>{v}</span></div>"
            for k, v in filas) + "</div>",
        unsafe_allow_html=True,
    )

    # Editores Take Profit / Stop Loss (toggle + Precio/Cantidad + Cancelar/Guardar).
    # Si el stop dinámico está activo, el Stop loss manual queda deshabilitado (el
    # auto gestiona ese mismo SL): no se puede editar ni quitar desde aquí.
    trailing_activo = int(ticket) in trailing_store.leer()
    with st.container(key=f"cad_tpbox_{ticket}"):
        _editor_nivel("tp", "Take profit", ticket, p, e, ap, ac, compra)
    with st.container(key=f"cad_slbox_{ticket}"):
        _editor_nivel("sl", "Stop loss", ticket, p, e, ap, ac, compra, bloqueado=trailing_activo)
    with st.container(key=f"cad_trailbox_{ticket}"):
        _editor_trailing(ticket, p, e)
