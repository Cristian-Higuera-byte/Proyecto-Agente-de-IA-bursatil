"""
cartera_panel.py
----------------
Lista de CARTERA (posiciones abiertas) que reemplaza al watchlist en la vista
de Trading cuando el usuario entra a "Cartera". Misma estética que la watchlist;
cada fila es clicable y carga ese símbolo en el gráfico central. Los datos salen
en vivo de MT5 (tools.mt5_bridge.obtener_posiciones).
"""
import html
import re
import time
from datetime import datetime, timedelta

import streamlit as st

from components.live_feed import intervalo as _intervalo
from tools.mt5_bridge import (obtener_posiciones, cerrar_posicion,
                              modificar_sltp, especs_posicion, obtener_historial)
from tools import watchlist_manager as wl
from tools import trailing_store
from tools import cerradas_store

from components.iconos import icono_activo   # íconos estilo XM (comunes a todo el dashboard)

ALTURA_LISTA = 700

_CSS = """
<style>
  div[data-testid="stElementContainer"]:has(.ca-css),
  div[data-testid="element-container"]:has(.ca-css) { display:none; }

  .st-key-ca_panel { background:#0d1117; border:1px solid #1f2937; border-radius:14px; overflow:hidden; margin-top:-30px; }
  .st-key-ca_panel, .st-key-ca_panel [data-testid="stVerticalBlock"],
  .st-key-ca_scroll { gap:0 !important; }
  .st-key-ca_panel div[data-testid="stVerticalBlockBorderWrapper"] { background:transparent !important; border:none !important; }
  .st-key-ca_panel div[data-testid="stMarkdownContainer"] { margin-bottom:0 !important; }

  /* ---- Encabezado ---- */
  .ca-head { display:flex; align-items:center; gap:11px; padding:16px 16px 13px; position:relative; z-index:2; }
  .ca-head .ic { width:38px; height:38px; border-radius:11px; flex:0 0 auto; display:flex;
      align-items:center; justify-content:center;
      background:linear-gradient(135deg,rgba(255,75,75,.16),rgba(255,143,0,.16)); border:1px solid #2a2320; }
  .ca-mi { font-family:'Material Symbols Rounded'; font-weight:400; font-size:21px; line-height:1;
      background:linear-gradient(135deg,#ff6a3d,#ff8f00); -webkit-background-clip:text; background-clip:text; color:transparent; }
  .ca-title { font-size:16px; font-weight:800; color:#fff; letter-spacing:.2px; line-height:1.1; }
  .ca-sub { font-size:11.5px; color:#8b949e; margin-top:2px; }

  /* ---- P/G total (tarjeta) ---- */
  .ca-totals { margin:0 14px 6px; padding:13px 15px; border-radius:12px; background:#0f1620;
      border:1px solid #202a37; display:flex; align-items:center; justify-content:space-between; position:relative; z-index:2; }
  .ca-totals .lbl { font-size:10.5px; color:#8b949e; font-weight:700; text-transform:uppercase; letter-spacing:.5px; }
  .ca-totals .cnt { margin-left:7px; font-size:10px; color:#aeb7c2; background:#1a2130;
      border-radius:999px; padding:2px 8px; letter-spacing:0; }
  .ca-totals .val { font-size:20px; font-weight:800; font-variant-numeric:tabular-nums; letter-spacing:.2px; }

  /* ---- Lista ---- */
  .st-key-ca_scroll { scrollbar-gutter:stable both-edges; scrollbar-width:thin; scrollbar-color:#2b3550 transparent;
      padding:4px 14px 12px; }
  .st-key-ca_scroll::-webkit-scrollbar { width:6px; }
  .st-key-ca_scroll::-webkit-scrollbar-thumb { background:#2b3550; border-radius:3px; }

  [class*="st-key-carow_"] { position:relative; overflow:hidden; margin-bottom:9px; }
  [class*="st-key-carow_"] div[data-testid="stElementContainer"],
  [class*="st-key-carow_"] div[data-testid="element-container"],
  [class*="st-key-carow_"] div[data-testid="stMarkdownContainer"],
  [class*="st-key-carow_"] div[data-testid="stMarkdown"] { margin:0 !important; }

  /* ---- Tarjeta de posición ---- */
  .ca-row { display:flex; align-items:center; gap:12px; padding:13px 44px 13px 15px;
      background:#151c27; border:1px solid #202a37; border-radius:12px; box-sizing:border-box;
      line-height:1.3; position:relative; overflow:hidden; transition:border-color .14s ease, background .14s ease; }
  .ca-row::before { content:""; position:absolute; left:0; top:0; bottom:0; width:3px; border-radius:3px 0 0 3px; }
  .ca-row.buy::before  { background:linear-gradient(180deg,#3fb950,#2ea043); }
  .ca-row.sell::before { background:linear-gradient(180deg,#f85149,#da3633); }
  [class*="st-key-carow_"]:hover .ca-row { border-color:#30405a; background:#192231; }
  .ca-row.sel { border-color:#36465f; background:#19212e; border-radius:12px 12px 0 0; }

  .ca-ico { flex:0 0 auto; display:flex; align-items:center; }
  .ca-mid { flex:1 1 auto; min-width:0; overflow:hidden; }
  .ca-tk { font-size:14.5px; font-weight:700; color:#fff; white-space:nowrap; overflow:hidden;
      text-overflow:ellipsis; display:flex; align-items:center; gap:7px; }
  .ca-badge { font-size:9.5px; font-weight:800; letter-spacing:.6px; padding:2px 6px; border-radius:5px; flex:0 0 auto; }
  .ca-badge.buy  { background:rgba(63,185,80,.15);  color:#3fb950; }
  .ca-badge.sell { background:rgba(248,81,73,.15);  color:#f6465d; }
  .ca-meta { font-size:11.5px; color:#8b949e; margin-top:4px; white-space:nowrap; overflow:hidden;
      text-overflow:ellipsis; font-variant-numeric:tabular-nums; }
  .ca-right { text-align:right; flex:0 0 auto; white-space:nowrap; display:flex; align-items:center; gap:8px; }
  .ca-plwrap { text-align:right; }
  .ca-pl { font-size:15.5px; font-weight:800; font-variant-numeric:tabular-nums; }
  .ca-opn { font-size:11px; color:#8b949e; margin-top:3px; font-variant-numeric:tabular-nums; }
  .ca-caret { color:#5a6676; font-size:11px; transition:color .14s ease; }
  [class*="st-key-carow_"]:hover .ca-caret { color:#8b949e; }
  .ca-buy { color:#2ebd85; }
  .ca-sell { color:#f6465d; }
  .ca-up { color:#2ebd85; } .ca-down { color:#f6465d; }

  [class*="st-key-casel_"] { position:absolute !important; top:0 !important; right:0 !important; bottom:0 !important;
      left:0 !important; width:100% !important; height:100% !important; margin:0 !important; padding:0 !important; z-index:1; }
  [class*="st-key-casel_"] * { width:100% !important; height:100% !important; min-height:0 !important; margin:0 !important; padding:0 !important; }
  [class*="st-key-casel_"] button { opacity:0; cursor:pointer; }

  /* Botón X para cerrar la posición (por encima del overlay de selección) */
  [class*="st-key-cacls_"] { position:absolute !important; right:11px; top:13px;
      width:28px !important; margin:0 !important; z-index:2; }
  [class*="st-key-cacls_"] * { margin:0 !important; }
  [class*="st-key-cacls_"] button { width:28px !important; height:28px !important; min-height:28px !important;
      padding:0 !important; background:transparent !important; border:none !important; box-shadow:none !important;
      color:#6b7686 !important; border-radius:8px !important; font-size:14px !important; cursor:pointer;
      transition:background .14s ease, color .14s ease; }
  [class*="st-key-cacls_"] button:hover { background:rgba(248,81,73,0.16) !important; color:#f85149 !important; }

  .ca-empty { padding:40px 20px; text-align:center; color:#8b949e; font-size:13px; line-height:1.6; }
  .ca-result-ok { color:#2ebd85; font-size:13px; padding:8px 14px; }
  .ca-result-err { color:#f85149; font-size:13px; padding:8px 14px; }

  /* ---- Tarjetas de posiciones CERRADAS (aviso con "Aceptar") ---- */
  [class*="st-key-cacerr_"] { margin:0 0 9px; }
  [class*="st-key-cacerr_"] div[data-testid="stElementContainer"],
  [class*="st-key-cacerr_"] div[data-testid="stMarkdownContainer"] { margin:0 !important; }
  .ca-closed { background:#12161d; border:1px dashed #33425c; border-radius:12px; padding:12px 14px;
      box-sizing:border-box; width:100%; overflow:hidden; }
  .cc-top { display:flex; align-items:center; gap:10px; }
  .cc-ico { flex:0 0 auto; display:flex; align-items:center; opacity:.8; }
  .cc-sym { font-size:14px; font-weight:700; color:#c3ccd6; display:flex; align-items:center; gap:7px; min-width:0; }
  .cc-badge { font-size:9px; font-weight:800; letter-spacing:.6px; padding:2px 6px; border-radius:5px; }
  .cc-badge.buy  { background:rgba(63,185,80,.12); color:#5fae6a; }
  .cc-badge.sell { background:rgba(248,81,73,.12); color:#c56a66; }
  .cc-tag { font-size:9px; font-weight:800; letter-spacing:.6px; padding:2px 6px; border-radius:5px;
      background:#232e42; color:#8b9bb4; }
  .cc-pl { margin-left:auto; font-size:15px; font-weight:800; font-variant-numeric:tabular-nums; }
  .cc-grid { margin-top:9px; border-top:1px solid #1c2531; padding-top:8px;
      display:flex; flex-wrap:wrap; gap:4px 18px; }
  .cc-grid .it { font-size:12px; color:#8b949e; }
  .cc-grid .it b { color:#c9d1d9; font-weight:600; font-variant-numeric:tabular-nums; }
  [class*="st-key-cacerr_"] button { background:#1a2130 !important; border:1px solid #33425c !important;
      color:#c3ccd6 !important; height:34px !important; min-height:34px !important;
      border-radius:9px !important; margin-top:9px !important; font-size:13px !important; }
  [class*="st-key-cacerr_"] button:hover { border-color:#58a6ff !important; color:#fff !important; background:#21304a !important; }
</style>
"""



def _neto(p: dict) -> float:
    """P/G neto de una posición (profit + swap), como lo suma MT5 en la cuenta."""
    return float(p.get("profit", 0.0) or 0.0) + float(p.get("swap", 0.0) or 0.0)


def _fmtp(x) -> str:
    """Precio sin ceros finales (no tenemos los dígitos del símbolo aquí)."""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return (f"{x:,.5f}".rstrip("0").rstrip(".")) if x else "—"


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
            cerradas_store.guardar(st.session_state.ca_cerradas)   # sobrevive al F5
            if st.session_state.get("ca_detalle") in cerr:
                st.session_state.ca_detalle = None   # cierra el detalle de la que se cerró
    # Foto actual para la próxima comparación.
    st.session_state.ca_prev = {
        p.get("ticket"): {"sym": wl.nombre_visible(p["symbol"]), "real": p["symbol"],
                          "side": p.get("tipo", ""), "volumen": p.get("volumen", 0),
                          "ap": float(p.get("precio_apertura", 0) or 0),
                          "ac": float(p.get("precio_actual", 0) or 0), "pg": _neto(p)}
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
                f"<span class='it'>Apertura <b>{_fmtp(c.get('ap'))}</b></span>"
                f"<span class='it'>Cierre <b>{_fmtp(c.get('cierre', c.get('ac')))}</b></span>"
                f"<span class='it'>Hora <b>{c.get('hora', '')}</b></span>"
                "</div></div>",
                unsafe_allow_html=True,
            )
            if st.button("Aceptar", key=f"cacerr_ok_{tk}", width="stretch"):
                st.session_state.ca_cerradas = [x for x in cerradas if x["ticket"] != tk]
                cerradas_store.guardar(st.session_state.ca_cerradas)
                st.rerun()

def renderizar_cartera_lista():
    """Panel de posiciones abiertas (reemplaza al watchlist en 'Cartera')."""
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown(_CSS_DET, unsafe_allow_html=True)
    pos = obtener_posiciones()
    st.session_state.ca_editando = False   # lo activan los editores si abren un input
    # Tras un F5 la sesión es nueva: recuperar las tarjetas cerradas del archivo.
    if "ca_cerradas" not in st.session_state:
        st.session_state.ca_cerradas = cerradas_store.leer()
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
        total = sum(_neto(p) for p in pos) if pos else 0.0
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
                prof = _neto(p)
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
                    _detalle_inline(tk, p)


# --- Modal de confirmación de cierre (se renderiza FUERA del fragmento, en
#     app.py, como el buscador, para no chocar con el auto-refresco) ---
def _al_descartar():
    """Clic fuera del modal / Esc: se descarta la intención de cierre (si no,
    el modal reaparecería en la siguiente reejecución)."""
    st.session_state.ca_cerrar = None


def texto_cerrar(prof: float) -> str:
    """Texto del botón estilo XM: 'Cerrar con pérdida de -$220.00' /
    'Cerrar con ganancia de $280.00'. (live_feed.py usa el mismo formato.)"""
    verbo = "ganancia" if prof >= 0 else "pérdida"
    signo = "-" if prof < 0 else ""
    return f"Cerrar con {verbo} de {signo}${abs(prof):,.2f}"


# Estilo copiado del modal de XM: tarjeta azul oscuro redondeada, sin "X",
# botón grande con el monto (naranja P&J en vez del azul de XM) y "Cancelar" con borde. Todo acotado con :has()
# a ESTE modal (el contenedor del botón se llama ca_btncerrar_<ticket>).
_SEL = "[data-testid='stDialog']:has([class*='st-key-ca_btncerrar_'])"
_CSS_MODAL = f"""
<style>
  /* Centrado: el fondo del diálogo (Streamlit 1.64) es un flex con
     align-items:flex-start; el diálogo es un section, no un div. */
  {_SEL} {{ align-items:center !important; background:rgba(5,8,15,.55) !important; }}
  /* Colores de la paleta del dashboard (paneles #0d1117, bordes #30363d) */
  {_SEL} > div {{
    background:#0d1117 !important; border:1px solid #30363d !important;
    border-radius:16px !important;
    width:460px !important; max-width:calc(100% - 32px) !important;
    box-shadow:0 18px 50px rgba(0,0,0,.55) !important;
  }}
  {_SEL} button[aria-label='Close'] {{ display:none !important; }}
  {_SEL} h2, {_SEL} [slot='title'] {{
    color:#ffffff !important; font-size:25px !important; font-weight:700 !important;
    padding:30px 30px 10px !important;
  }}
  {_SEL} [data-testid='stVerticalBlock'] {{ gap:14px !important; }}
  {_SEL} .st-key-ca_cerrar_ok button,
  {_SEL} .st-key-ca_cerrar_cancel button {{
    height:70px !important; border-radius:12px !important; width:100% !important;
  }}
  /* Botón principal con el naranja del logo P&J (mismo degradado que nav_bar.py) */
  {_SEL} .st-key-ca_cerrar_ok button {{
    background:linear-gradient(135deg,#ff4b4b 0%,#ff8f00 100%) !important;
    border:none !important; color:#ffffff !important;
  }}
  {_SEL} .st-key-ca_cerrar_ok button:hover {{ filter:brightness(1.1) !important; }}
  {_SEL} .st-key-ca_cerrar_cancel button {{
    background:#161b22 !important; border:1px solid #30363d !important; color:#ffffff !important;
  }}
  {_SEL} .st-key-ca_cerrar_cancel button:hover {{ border-color:#58a6ff !important; background:#21262d !important; }}
  {_SEL} .st-key-ca_cerrar_ok button p,
  {_SEL} .st-key-ca_cerrar_cancel button p {{
    font-size:20px !important; font-weight:700 !important; color:#ffffff !important;
  }}
</style>
"""


@st.dialog("¿Quiere cerrar su posición?", on_dismiss=_al_descartar)
def _dialogo_cerrar():
    c = st.session_state.get("ca_cerrar") or {}
    ticket = c.get("ticket")
    # P/G FRESCO de MT5 al abrir (el de la fila podía tener hasta 5 s de atraso:
    # la fila la pinta el feed en vivo, pero el dato guardado era del último refresco).
    prof = c.get("profit", 0.0)
    try:
        fresca = next((p for p in obtener_posiciones() if p.get("ticket") == ticket), None)
        if fresca:
            prof = _neto(fresca)
    except Exception:
        pass
    st.markdown(_CSS_MODAL, unsafe_allow_html=True)
    etiqueta = texto_cerrar(prof)
    # El contenedor lleva el ticket en su clave: live_feed.py actualiza el texto
    # del botón en vivo con el P/G neto de esa posición (mismo dato que la fila).
    with st.container(key=f"ca_btncerrar_{ticket}"):
        cerrar = st.button(etiqueta, type="primary", width="stretch", key="ca_cerrar_ok")
    if cerrar:
        res = cerrar_posicion(c.get("ticket"))
        if "error" in res:
            st.session_state.ca_result = ("error", f"No se pudo cerrar: {res['error']}")
        else:
            # P/G exacto para la tarjeta de posición cerrada (lo usa _detectar_cierres).
            st.session_state.setdefault("ca_pg_real", {})[c.get("ticket")] = float(res.get("profit", prof))
            st.session_state.pop("ca_result", None)
        st.session_state.ca_cerrar = None
        st.rerun()
    if st.button("Cancelar", width="stretch", key="ca_cerrar_cancel"):
        st.session_state.ca_cerrar = None
        st.rerun()


def render_modal_cerrar():
    """Llamar desde app.py (fuera de los fragmentos en vivo)."""
    if st.session_state.get("ca_cerrar"):
        _dialogo_cerrar()


# ======================================================================
#  DETALLE DESPLEGABLE DE LA POSICIÓN (acordeón inline en la Cartera, como XM)
#  Al tocar una posición se despliega, justo debajo de su fila, toda la info,
#  el botón de cierre, "Mostrar gráfico" y los editores de Take Profit /
#  Stop Loss. El P/G y el precio actual se pintan en vivo por el feed; mientras
#  una fila está desplegada, app.py pausa el auto-refresco del fragmento.
# ======================================================================
_CSS_DET = """
<style>
  [class*="st-key-cadet_wrap_"] { background:#141c28; border:1px solid #36465f;
      border-top:1px solid #243049; border-radius:0 0 12px 12px;
      padding:13px 15px 15px; margin-top:-9px; margin-bottom:9px; }
  [class*="st-key-cadet_wrap_"] [data-testid="stVerticalBlock"] { gap:10px !important; }
  [class*="st-key-cadet_wrap_"] div[data-testid="stMarkdownContainer"] { margin-bottom:0 !important; }

  .cad-grid { border-top:1px solid #1f2937; }
  .cad-grid .row { display:flex; justify-content:space-between; gap:12px; padding:4px 2px;
      border-bottom:1px solid #141a22; font-size:13px; }
  .cad-grid .k { color:#8b949e; }
  .cad-grid .v { color:#e6edf3; font-weight:600; text-align:right;
      font-variant-numeric:tabular-nums; }
  .cad-up { color:#2ebd85 !important; } .cad-down { color:#f6465d !important; }
  .cad-note { color:#8b949e; font-size:11.5px; margin:2px 2px 4px; }
  .cad-err { color:#f85149; font-size:12px; margin:4px 2px 8px; }
  .cad-trail-on { display:flex; align-items:center; justify-content:space-between; gap:10px;
      padding:9px 12px; border-radius:10px; background:#111a16; border:1px solid #1e3a2a; margin:2px 0 4px; }
  .cad-trail-on .k { color:#2ebd85; font-size:12.5px; font-weight:700; }
  .cad-trail-on .v { color:#e6edf3; font-size:12.5px; font-variant-numeric:tabular-nums; }
  .cad-fb-ok { color:#2ebd85; font-size:13px; padding:4px 2px; }
  .cad-fb-err { color:#f85149; font-size:13px; padding:4px 2px; }
  .cad-empty { color:#8b949e; font-size:13px; padding:16px 6px; text-align:center; }

  [class*="st-key-cadet_cerrar_"] { margin-bottom:10px !important; }
  [class*="st-key-cadet_cerrar_"] button {
      background:linear-gradient(135deg,#ff4b4b 0%,#ff8f00 100%) !important; border:none !important;
      color:#fff !important; height:48px !important; border-radius:10px !important; }
  [class*="st-key-cadet_cerrar_"] button:hover { filter:brightness(1.08) !important; }
  [class*="st-key-cadet_cerrar_"] button p { font-size:15px !important; font-weight:700 !important; color:#fff !important; }
  .st-key-cadet_grafico { margin-bottom:8px !important; }
  .st-key-cadet_grafico button {
      background:#161b22 !important; border:1px solid #30363d !important; color:#e6edf3 !important;
      height:42px !important; border-radius:10px !important; }
  .st-key-cadet_grafico button:hover { border-color:#58a6ff !important; background:#21262d !important; }
  /* Guardar en el degradado P&J cuando está habilitado */
  [class*="st-key-cad_"][class*="_guardar_"] button[kind="primary"] {
      background:linear-gradient(135deg,#ff4b4b 0%,#ff8f00 100%) !important; border:none !important; color:#fff !important; }
  [class*="st-key-cad_"][class*="_guardar_"] button:disabled {
      background:#1b2230 !important; border:1px solid #273142 !important; color:#5a6676 !important; }
</style>
"""


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


def _detalle_inline(ticket, p):
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
        neto = _neto(p)
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
        signo = "-" if neto < 0 else ""
        with st.container(key=f"cadet_cerrar_{ticket}"):
            if st.button(f"Cerrar operación: {signo}${abs(neto):,.2f}", key="cadet_btncerrar",
                         type="primary", width="stretch"):
                st.session_state.ca_cerrar = {
                    "ticket": ticket, "symbol": base, "profit": neto,
                    "tipo": lado, "volumen": p.get("volumen", 0),
                }
                st.session_state.pop("ca_result", None)
                st.rerun(scope="app")
        if st.button("Mostrar gráfico", key="cadet_grafico", width="stretch"):
            st.session_state.activo_seleccionado = sym
            # Se mantiene el desplegable abierto (no se limpia ca_detalle).
            st.rerun()

        _grid_y_editores(ticket, p, e, sym, lado, compra, neto, ap, ac, dig, var)


def _grid_y_editores(ticket, p, e, sym, lado, compra, neto, ap, ac, dig, var):
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
        ("PnL", f"<span class='{'cad-up' if neto >= 0 else 'cad-down'}' data-pj-pos='{ticket}' "
                f"data-pj-up='#2ebd85' data-pj-dn='#f6465d'>{neto:+,.2f}</span>"),
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
