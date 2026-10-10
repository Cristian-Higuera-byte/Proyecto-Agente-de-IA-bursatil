"""
order_panel.py
--------------
Ticket de orden (comprar / vender) a la derecha del gráfico, con el diseño de XM:
- "One-Click Trading" con el interruptor a la derecha (si está apagado, pide confirmación;
  la primera vez que se activa exige aceptar los términos: components/one_click.py).
- SELL | BUY unidos (el lado elegido se pinta en rojo/verde) + spread al centro.
- Cantidad / Lotes a todo el ancho y el volumen en una tarjeta con la etiqueta
  DENTRO y el número grande (como XM).
- Margen requerido + barra con el % del margen libre que usaría la orden.
- Tarjeta "Pending order" (Buy/Sell Limit o Stop según el precio) con
  "Good till cancelled (GTC)", y tarjeta de Take Profit / Stop Loss.
Términos de trading en INGLÉS (decisión del equipo, 06-10-2026); el resto en español.
- Botón grande "Colocar orden en {precio}" del color del lado elegido.

Las órdenes se envían a la cuenta CONECTADA en MetaTrader 5 (demo en desarrollo)
vía tools.mt5_bridge. El usuario confirma cada operación (salvo One-Click Trading).
El estilo usa CSS acotado a las claves de este panel (.st-key-ord_*); el ancho del
panel lo define app.py (no se toca aquí).
"""
import json
import time

import streamlit as st
import streamlit.components.v1 as components
import MetaTrader5 as mt5  # type: ignore[import-untyped]

from components.live_feed import attrs as _live, intervalo as _intervalo
from components.one_click import al_cambiar as _oc_cambiar, pedir_terminos_si_corresponde

from tools.mt5_bridge import (
    MT5_LOCK, inicializar_mt5, obtener_precio_actual, resolver_simbolo,
    ejecutar_orden_mercado, colocar_orden_pendiente, eliminar_orden,
)
from tools import oco_store

_CSS = """
<style>
  /* ====== Tarjeta del panel ====== */
  .st-key-ord_panel { background:#0f1620; border:1px solid #202a37; border-radius:14px;
      padding:16px 14px 16px; }
  .st-key-ord_panel [data-testid="stVerticalBlock"] { gap:12px; }
  .ord-h { color:#e6edf3; font-weight:800; font-size:16px; margin:0 0 2px; }
  .ord-sub { color:#8b949e; font-size:12px; margin:0; }

  /* ====== Interruptores: texto a la izquierda, switch a la derecha, verde ======
     Estructura de Streamlit 1.64 (medida en el navegador): stCheckbox > label >
     [span con el input oculto] + [div = riel del switch] + [div = texto]. El
     contenedor viene con width="fit-content", por eso se fuerza al 100 %. */
  [class*="st-key-ord_tg_"] [data-testid="stElementContainer"],
  [class*="st-key-ord_tg_"] [data-testid="stCheckbox"] { width:100% !important; }
  [class*="st-key-ord_tg_"] [data-testid="stCheckbox"] label {
      display:flex !important; flex-direction:row-reverse; justify-content:space-between;
      align-items:center; width:100%; gap:12px; }
  [class*="st-key-ord_tg_"] [data-testid="stCheckbox"] label p {
      color:#e6edf3 !important; font-size:14px !important; font-weight:600 !important;
      line-height:1.3 !important; }
  [class*="st-key-ord_tg_"] [data-testid="stCheckbox"] label:has(input:checked) > span + div {
      background:#2ea043 !important; }
  [class*="st-key-ord_tg_"] [data-testid="stTooltipIcon"] { display:none !important; }

  /* ====== VENTA | COMPRA unidos (como XM) ====== */
  .ord-join { position:relative; display:flex; border-radius:12px; overflow:hidden;
      border:1px solid #252f3d; }
  .ord-half { flex:1; min-width:0; overflow:hidden; padding:10px 12px; box-sizing:border-box;
      background:#151c27; transition:background .12s ease; }
  .ord-half .ord-lbl { font-size:11px; font-weight:700; letter-spacing:.4px; white-space:nowrap;
      color:#8b949e; }
  .ord-half .ord-px { font-size:15px; font-weight:800; margin-top:2px; white-space:nowrap;
      overflow:hidden; text-overflow:ellipsis; color:#8b949e;
      font-family:ui-monospace,Consolas,monospace; }
  .ord-sell { text-align:left; }
  .ord-buy { text-align:right; }
  .ord-sell.sel { background:linear-gradient(135deg,#f85149,#da3633); }
  .ord-buy.sel  { background:linear-gradient(135deg,#3fb950,#2ea043); }
  .ord-half.sel .ord-lbl, .ord-half.sel .ord-px { color:#ffffff; }
  .ord-spread { position:absolute; left:50%; top:50%; transform:translate(-50%,-50%);
      background:#e9edf2; color:#111820; font-size:12px; font-weight:800;
      border-radius:8px; padding:3px 8px; font-family:ui-monospace,Consolas,monospace;
      pointer-events:none; z-index:4; box-shadow:0 1px 4px rgba(0,0,0,.35); }

  /* Botones invisibles que hacen clicable cada mitad / el botón grande */
  [class*="st-key-ord_bx"] { position:relative; }
  [class*="st-key-ord_ov"] { position:absolute !important; inset:0 !important;
      width:100% !important; height:100% !important; margin:0 !important;
      padding:0 !important; z-index:3; }
  [class*="st-key-ord_ov"] * { width:100% !important; height:100% !important;
      min-height:0 !important; margin:0 !important; padding:0 !important; }
  [class*="st-key-ord_ov"] button { opacity:0; cursor:pointer; }
  [class*="st-key-ord_ovsell"] { right:auto !important; width:50% !important; }
  [class*="st-key-ord_ovbuy"]  { left:auto !important;  width:50% !important; }

  /* ====== Cantidad | Lotes (segmentado a todo el ancho) ====== */
  .st-key-ord_modo [data-testid="stButtonGroup"],
  .st-key-ord_oco_lado [data-testid="stButtonGroup"],
  .st-key-ord_rm_modo [data-testid="stButtonGroup"] { width:100%; }
  .st-key-ord_modo [role="radiogroup"],
  .st-key-ord_oco_lado [role="radiogroup"],
  .st-key-ord_rm_modo [role="radiogroup"] { width:100%; display:flex;
      background:#0d1117; border:1px solid #252f3d; border-radius:10px; padding:3px; gap:3px; }
  .st-key-ord_modo button, .st-key-ord_oco_lado button, .st-key-ord_rm_modo button {
      flex:1 1 0; border:none !important; border-radius:8px !important;
      background:transparent !important; min-height:36px !important; box-shadow:none !important; }
  .st-key-ord_modo button p, .st-key-ord_oco_lado button p, .st-key-ord_rm_modo button p {
      color:#c9d1d9 !important; font-size:14px !important; font-weight:700 !important; }
  .st-key-ord_modo button[aria-checked="true"],
  .st-key-ord_oco_lado button[aria-checked="true"],
  .st-key-ord_rm_modo button[aria-checked="true"] { background:#2a3342 !important; }
  .st-key-ord_modo button[aria-checked="true"] p,
  .st-key-ord_oco_lado button[aria-checked="true"] p,
  .st-key-ord_rm_modo button[aria-checked="true"] p { color:#ffffff !important; }

  /* Botón "Aplicar al ticket" (Calculadora de riesgo) */
  .st-key-ord_rm_aplicar button { background:#1f6feb !important; border:none !important; }
  .st-key-ord_rm_aplicar button p { color:#fff !important; font-weight:700 !important; }

  /* ====== Campos tipo tarjeta: etiqueta DENTRO + número grande ====== */
  [class*="st-key-ord_box_"] { position:relative; }
  [class*="st-key-ord_box_"] [data-testid="stVerticalBlock"] { gap:0 !important; }
  [class*="st-key-ord_box_"] [data-testid="stElementContainer"]:has(.ord-box-lbl) {
      position:absolute !important; inset:0; z-index:2; pointer-events:none; }
  .ord-box-lbl { position:absolute; top:9px; left:15px; color:#8b949e; font-size:12px; }
  .ord-box-suf { position:absolute; right:15px; bottom:13px; color:#8b949e; font-size:14px;
      font-weight:600; }
  [class*="st-key-ord_box_"] [data-testid="stNumberInputContainer"] {
      background:#0d1117 !important; border:1px solid #2b3546 !important;
      border-radius:12px !important; height:62px; }
  [class*="st-key-ord_box_"] [data-testid="stNumberInputContainer"]:focus-within {
      border-color:#2f81f7 !important; box-shadow:0 0 0 1px #2f81f7 !important; }
  [class*="st-key-ord_box_"] input {
      font-size:20px !important; font-weight:700 !important; color:#ffffff !important;
      padding:22px 15px 6px !important; background:transparent !important;
      font-family:ui-monospace,Consolas,monospace !important; }
  /* + / − como en XM: apilados a la derecha y visibles SOLO al pasar el mouse.
     En Streamlit 1.64 van en un div después del input: [StepDown][StepUp];
     OJO: no escribir etiquetas HTML dentro de este CSS (ni en comentarios):
     el sanitizador de st.html elimina el bloque de estilos completo.
     column-reverse deja el + arriba. */
  [class*="st-key-ord_box_"] [data-testid="stNumberInputContainer"] { position:relative; }
  [class*="st-key-ord_box_"] [data-testid="stNumberInputContainer"] > div {
      position:absolute; right:8px; top:50%; transform:translateY(-50%); z-index:3;
      display:flex; flex-direction:column-reverse; gap:3px;
      opacity:0; pointer-events:none; transition:opacity .15s ease; }
  [class*="st-key-ord_box_"]:hover [data-testid="stNumberInputContainer"] > div,
  [class*="st-key-ord_box_"] [data-testid="stNumberInputContainer"]:focus-within > div {
      opacity:1; pointer-events:auto; }
  [class*="st-key-ord_box_"] [data-testid="stNumberInputStepUp"],
  [class*="st-key-ord_box_"] [data-testid="stNumberInputStepDown"] {
      width:26px !important; height:23px !important; min-height:0 !important; padding:0 !important;
      background:#2a3342 !important; border:none !important; border-radius:6px !important;
      color:#e6edf3 !important; display:flex; align-items:center; justify-content:center; }
  [class*="st-key-ord_box_"] [data-testid="stNumberInputStepUp"]:hover,
  [class*="st-key-ord_box_"] [data-testid="stNumberInputStepDown"]:hover { background:#3a4558 !important; }
  [class*="st-key-ord_box_"] [data-testid="stNumberInputStepDown"]:disabled { opacity:.35; }
  .ord-box-suf { transition:right .15s ease; }
  [class*="st-key-ord_box_"]:hover .ord-box-suf,
  [class*="st-key-ord_box_"]:focus-within .ord-box-suf { right:44px; }

  /* ====== Margen ====== */
  .ord-margen { color:#8b949e; font-size:13px; display:flex; gap:6px; align-items:baseline; }
  .ord-margen b { color:#e6edf3; font-weight:700; }
  .ord-mbar-row { display:flex; align-items:center; gap:12px; margin-top:8px; }
  .ord-mbar { flex:1; height:6px; border-radius:6px; background:#2b3546; overflow:hidden; }
  .ord-mbar > div { height:100%; border-radius:6px; transition:width .2s ease; }
  .ord-mbar-pct { font-size:14px; font-weight:700; color:#e6edf3; min-width:58px;
      text-align:right; }
  .ord-sin-margen { color:#f85149; font-size:13px; font-weight:600; margin-top:6px; }
  .ord-hint { color:#8b949e; font-size:12px; }
  .ord-hint b { display:block; color:#e6edf3; font-size:14px; margin-top:2px;
      font-family:ui-monospace,Consolas,monospace; }

  /* ====== Tarjetas agrupadas (orden pendiente / TP-SL) ====== */
  [class*="st-key-ord_card_"] { background:#151c27; border:1px solid #252f3d;
      border-radius:12px; padding:12px 14px; }
  [class*="st-key-ord_card_"] [data-testid="stVerticalBlock"] { gap:10px; }
  .ord-sep { height:1px; background:#252f3d; margin:2px -14px; }

  /* ====== Botón grande "Colocar orden en" ====== */
  .ord-place { display:flex; align-items:center; justify-content:space-between;
      border-radius:12px; padding:13px 18px; min-height:64px; }
  .ord-place .pl-lbl { font-size:13px; color:rgba(255,255,255,.92); }
  .ord-place .pl-px { font-size:22px; font-weight:800; color:#fff; line-height:1.15;
      white-space:nowrap; font-family:ui-monospace,Consolas,monospace; }
  .ord-place .pl-arrow { font-size:24px; color:#fff; font-weight:700; }
  .ord-place-buy  { background:linear-gradient(135deg,#3fb950,#2ea043); }
  .ord-place-sell { background:linear-gradient(135deg,#f85149,#da3633); }
  .ord-place-off { background:#1c2a24 !important; opacity:.6; }
  .ord-place-off .pl-lbl, .ord-place-off .pl-px, .ord-place-off .pl-arrow { color:#8b949e !important; }

  /* ====== Confirmación ====== */
  .ord-conf { background:#151c27; border:1px solid #2b3546; border-radius:12px;
      padding:12px 14px; color:#c9d1d9; font-size:13px; line-height:1.45; }
  .ord-conf b { color:#ffffff; }
  .ord-conf .t { color:#8b949e; font-size:12px; margin-bottom:4px; }
  .st-key-ord_ok button, .st-key-ord_oco_ok button { background:#2ea043 !important; border:none !important; }
  .st-key-ord_ok button p, .st-key-ord_oco_ok button p { color:#fff !important; font-weight:700 !important; }

  /* ====== Confirmación flotante (abajo-derecha del panel), formato naranja ====== */
  .st-key-ord_cfm { position:fixed !important; right:16px; bottom:16px;
      width:290px; max-width:calc(100% - 20px); z-index:100006;
      background:#0d1117; border:1px solid #30363d; border-radius:14px;
      padding:14px; box-shadow:0 14px 40px rgba(0,0,0,.6); }
  .st-key-ord_cfm [data-testid="stVerticalBlock"] { gap:10px !important; }
  .ord-cfm-t { color:#ffffff; font-weight:700; font-size:16px; margin:0 0 4px; }
  .ord-cfm-d { color:#c9d1d9; font-size:13px; line-height:1.5; }
  .ord-cfm-d b { color:#e6edf3; }
  .st-key-ord_cfm_ok button { background:linear-gradient(135deg,#ff4b4b,#ff8f00) !important;
      border:none !important; height:50px !important; border-radius:10px !important; }
  .st-key-ord_cfm_ok button p { color:#fff !important; font-weight:700 !important; font-size:16px !important; }
  .st-key-ord_cfm_ok button:hover { filter:brightness(1.1) !important; }
  .st-key-ord_cfm_cancel button { background:#161b22 !important; border:1px solid #30363d !important;
      height:44px !important; border-radius:10px !important; }
  .st-key-ord_cfm_cancel button p { color:#fff !important; font-weight:600 !important; }
  .st-key-ord_cfm_cancel button:hover { border-color:#58a6ff !important; background:#21262d !important; }

  /* Inyector del toast del resultado: sin tamaño (no ocupa espacio) */
  .st-key-ord_toastjs { position:absolute !important; width:0 !important; height:0 !important;
      overflow:hidden !important; }
</style>
"""


def _info_simbolo(real):
    try:
        with MT5_LOCK:
            mt5.symbol_select(real, True)
            return mt5.symbol_info(real)
    except Exception:
        return None


def _margen(real, volumen, precio, tipo):
    try:
        action = mt5.ORDER_TYPE_BUY if tipo == "BUY" else mt5.ORDER_TYPE_SELL
        with MT5_LOCK:
            return mt5.order_calc_margin(action, real, float(volumen), float(precio))
    except Exception:
        return None


def _margen_libre():
    """Margen libre de la cuenta (account_info().margin_free) o None."""
    try:
        with MT5_LOCK:
            cuenta = mt5.account_info()
        return float(cuenta.margin_free) if cuenta is not None else None
    except Exception:
        return None


def _capital_cuenta():
    """Equity y moneda de la cuenta (base de la Calculadora de riesgo): (equity, moneda)."""
    try:
        with MT5_LOCK:
            cuenta = mt5.account_info()
        if cuenta is None:
            return None, "USD"
        return float(cuenta.equity), getattr(cuenta, "currency", "USD") or "USD"
    except Exception:
        return None, "USD"


def _resultado(estado, msg):
    """Guarda el resultado de la orden + un nonce (para que el toast se muestre una vez)."""
    st.session_state.ord_result = (estado, msg)
    st.session_state.ord_result_nonce = f"{time.time()}"


def _ejecutar(real, visible, tipo, vol, sl, tp, pendiente=None, gtc=True):
    """Envía la orden a MT5: a mercado, o pendiente si `pendiente` trae un precio."""
    verbo = "Buy" if tipo == "BUY" else "Sell"
    if pendiente:
        res = colocar_orden_pendiente(real, tipo, vol, pendiente, sl, tp, hasta_cancelar=gtc)
        ok = (f"Pendiente colocada: {res.get('tipo', '')} de {vol:.2f} lote(s) de {visible} "
              f"a {res.get('price')}" + (" · GTC" if gtc else " · DAY (solo hoy)") + ".")
    else:
        res = ejecutar_orden_mercado(real, tipo, vol, sl, tp)
        verbo_es = "comprado" if tipo == "BUY" else "vendido"
        ok = (f"¡Listo! Has {verbo_es} {res.get('volume')} lote(s) de {visible} "
              f"a {res.get('price')}.")
    if "error" in res:
        _resultado("error", res["error"])
    else:
        _resultado("ok", ok)
    st.session_state.ord_confirm = None


def _ejecutar_oco(real, visible, lado_a, lado_b, precio_a, precio_b, vol, gtc=True):
    """Coloca las DOS patas de un OCO y las vincula en oco_store. Si falla la 2.ª,
    cancela la 1.ª para no dejar un par a medias. Las patas van sin SL/TP (suelen
    ir en lados opuestos: el SL/TP se define sobre la posición al ejecutarse)."""
    ra = colocar_orden_pendiente(real, lado_a, vol, precio_a, 0.0, 0.0, hasta_cancelar=gtc)
    if "error" in ra:
        _resultado("error", f"OCO: no se pudo colocar la 1.ª orden · {ra['error']}")
        st.session_state.ord_oco_confirm = None
        return
    rb = colocar_orden_pendiente(real, lado_b, vol, precio_b, 0.0, 0.0, hasta_cancelar=gtc)
    if "error" in rb:
        und = eliminar_orden(int(ra["order"]))
        extra = "" if "error" not in und else " (no se pudo deshacer la 1.ª: revísala en el gráfico)"
        _resultado("error",
                   f"OCO: no se pudo colocar la 2.ª orden · {rb['error']}. Se canceló la 1.ª{extra}.")
        st.session_state.ord_oco_confirm = None
        return
    oco_store.fijar(int(ra["order"]), int(rb["order"]), real)
    ok = (f"¡Listo! OCO colocado en {visible}: {ra.get('tipo')} {vol:.2f} @ {ra.get('price')} · "
          f"{rb.get('tipo')} {vol:.2f} @ {rb.get('price')}"
          + (" · GTC" if gtc else " · DAY (solo hoy)")
          + ". Cuando una se ejecute, la otra se cancela sola.")
    _resultado("ok", ok)
    st.session_state.ord_oco_confirm = None


# ---------------------------------------------------------------------------
# Confirmación en MODAL (estilo XM) y aviso tipo "toast" naranja
# ---------------------------------------------------------------------------
def _render_confirmacion():
    """Tarjeta de confirmación flotante (abajo-derecha del panel), formato naranja como
    el modal de cierre de Cartera. Se renderiza DENTRO del fragmento del ticket, así que
    los botones usan rerun de fragmento (instantáneo, sin recargar el gráfico)."""
    cf = st.session_state.get("ord_confirm")
    cfo = st.session_state.get("ord_oco_confirm")
    if not (cf or cfo):
        return
    with st.container(key="ord_cfm"):
        if cf:
            d, dig = cf, cf["dig"]
            if d["pend"]:
                modo = (f"Orden pendiente en <b>{d['price']:,.{dig}f}</b>"
                        + (" · GTC" if d["gtc"] else " · DAY"))
            else:
                # Orden a mercado: el precio se actualiza EN VIVO con el feed (como el ticket).
                _px = _live(d["real"], "side", d=dig, side=d["side"])
                modo = f"A mercado, ~<b {_px}>{d['price']:,.{dig}f}</b>"
            extra = ((f"<br>Stop Loss: <b>{d['sl']:,.{dig}f}</b>" if d["sl"] else "")
                     + (f"<br>Take Profit: <b>{d['tp']:,.{dig}f}</b>" if d["tp"] else ""))
            st.html(f"<div class='ord-cfm-t'>Confirmar orden</div>"
                    f"<div class='ord-cfm-d'><b>{d['side']}</b> de <b>{d['vol']:.2f}</b> lote(s) "
                    f"de <b>{d['visible']}</b><br>{modo}{extra}</div>")
            if st.button("Colocar orden", key="ord_cfm_ok", width="stretch"):
                m2, libre2 = _margen(d["real"], d["vol"], d["price"], d["side"]), _margen_libre()
                if m2 and libre2 is not None and m2 > libre2:
                    _resultado("error", "No tiene margen suficiente para colocar esta orden.")
                else:
                    _ejecutar(d["real"], d["visible"], d["side"], d["vol"], d["sl"],
                              d["tp"], d["pend"], d["gtc"])
                st.session_state.ord_confirm = None
                st.rerun(scope="fragment")
            if st.button("Cancelar", key="ord_cfm_cancel", width="stretch"):
                st.session_state.ord_confirm = None
                st.rerun(scope="fragment")
        else:
            d, dig = cfo, cfo["dig"]
            st.html(
                f"<div class='ord-cfm-t'>Confirmar OCO</div>"
                f"<div class='ord-cfm-d'>Dos órdenes de <b>{d['vol']:.2f}</b> lote(s) de "
                f"<b>{d['visible']}</b>{' · GTC' if d['gtc'] else ' · DAY'}:<br>"
                f"A: <b>{d['ta']} · {d['ladoA']}</b> @ <b>{d['pa']:,.{dig}f}</b><br>"
                f"B: <b>{d['tb']} · {d['ladoB']}</b> @ <b>{d['pb']:,.{dig}f}</b><br>"
                f"<span style='color:#8b949e'>Cuando una se ejecute, la otra se cancela sola.</span></div>")
            if st.button("Colocar OCO", key="ord_cfm_ok", width="stretch"):
                _ejecutar_oco(d["real"], d["visible"], d["ladoA"], d["ladoB"],
                              d["pa"], d["pb"], d["vol"], d["gtc"])
                st.session_state.ord_oco_confirm = None
                st.rerun(scope="fragment")
            if st.button("Cancelar", key="ord_cfm_cancel", width="stretch"):
                st.session_state.ord_oco_confirm = None
                st.rerun(scope="fragment")


def _toast_js(mensaje: str, es_error: bool, nonce: str) -> str:
    """Aviso flotante (toast) estilo XM: recuadro NARANJA (verde→naranja P&J) para éxito,
    rojo para error; se cierra solo a los ~6 s o con la ✕. Se inyecta en el documento
    padre y solo una vez por resultado (gracias al `nonce`)."""
    fondo = ("linear-gradient(135deg,#f85149,#da3633)" if es_error
             else "linear-gradient(135deg,#ff4b4b,#ff8f00)")
    icono = "&#9888;" if es_error else "&#10003;"
    n = json.dumps(str(nonce))
    msg = json.dumps(mensaje)
    return f"""
<script>
(function(){{
  var P = window.parent, D; try {{ D = P.document; }} catch(e) {{ return; }}
  if (P.__pjToastNonce === {n}) return;   // ya mostrado para este resultado
  P.__pjToastNonce = {n};
  var vj = D.getElementById('pj-toast'); if (vj) vj.remove();
  var el = D.createElement('div'); el.id = 'pj-toast';
  el.style.cssText = 'position:fixed;right:22px;bottom:56px;z-index:100010;max-width:380px;'+
    'display:flex;align-items:flex-start;gap:10px;padding:13px 14px;border-radius:12px;'+
    'background:{fondo};color:#fff;font:600 13.5px system-ui,sans-serif;'+
    'box-shadow:0 10px 30px rgba(0,0,0,.45);opacity:0;transform:translateY(8px);'+
    'transition:opacity .2s ease,transform .2s ease;';
  el.innerHTML = '<span style="font-size:18px;line-height:1.2">{icono}</span>'+
    '<span style="flex:1;line-height:1.4">'+{msg}+'</span>'+
    '<span id="pj-tx" style="cursor:pointer;opacity:.85;font-size:15px;padding:0 2px">&#10005;</span>';
  D.body.appendChild(el);
  P.requestAnimationFrame(function(){{ el.style.opacity='1'; el.style.transform='translateY(0)'; }});
  var tmr;
  function cerrar(){{
    if (!el) return;
    el.style.opacity='0'; el.style.transform='translateY(8px)';
    P.setTimeout(function(){{ if (el && el.parentNode) el.parentNode.removeChild(el); }}, 220);
    el = null; P.clearTimeout(tmr);
  }}
  el.querySelector('#pj-tx').onclick = cerrar;
  tmr = P.setTimeout(cerrar, 6000);
}})();
</script>
"""


def _campo(clave: str, etiqueta: str, sufijo: str = ""):
    """Contenedor de un campo tipo tarjeta: etiqueta dentro (arriba) + sufijo."""
    cont = st.container(key=f"ord_box_{clave}")
    cont.html(f"<div class='ord-box-lbl'>{etiqueta}</div>"
              + (f"<div class='ord-box-suf'>{sufijo}</div>" if sufijo else ""))
    return cont


def renderizar_panel_orden(main=None):
    inicializar_mt5()
    activo = st.session_state.get("activo_seleccionado", "EURUSD...")
    real = resolver_simbolo(activo)
    visible = activo.replace("...", "").strip()
    info = _info_simbolo(real)
    dig = int(getattr(info, "digits", 5) or 5) if info else 5
    vmin = float(getattr(info, "volume_min", 0.01) or 0.01) if info else 0.01
    vstep = float(getattr(info, "volume_step", 0.01) or 0.01) if info else 0.01
    point = getattr(info, "point", 0.0) if info else 0.0

    if "ord_side" not in st.session_state:
        st.session_state.ord_side = "BUY"

    st.html(_CSS)
    with st.container(key="ord_panel"):
        st.html(f"<div class='ord-h'>Operar · {visible}</div>"
                f"<div class='ord-sub'>Cuenta conectada en MT5 (demo)</div>")

        # TODO el ticket va dentro de UN fragmento cuyas acciones usan
        # scope="fragment" (nunca rerun de app desde aquí → sin parpadeo).
        @st.fragment(run_every=_intervalo("2s"))   # con feed: precios/spread por live_feed.py
        def _ticket():
            t = obtener_precio_actual(real)
            if "error" in t:
                st.caption("Sin precio en vivo. ¿Está abierto MetaTrader 5?")
                return
            bid, ask = t.get("bid", 0), t.get("ask", 0)
            side = st.session_state.get("ord_side", "BUY")
            compra = side == "BUY"

            # La Calculadora de riesgo pide "Aplicar" dejando los valores aquí; se vuelcan
            # a los widgets del ticket ANTES de crearlos (si no, Streamlit no deja cambiarlos).
            pend_rm = st.session_state.pop("_rm_aplicar", None)
            if pend_rm:
                st.session_state["ord_modo"] = "Lotes"
                st.session_state["ord_vol"] = pend_rm["vol"]
                if pend_rm.get("sl") or pend_rm.get("tp"):
                    st.session_state["ord_tpsl"] = True
                    if pend_rm.get("sl"):
                        st.session_state["ord_sl"] = pend_rm["sl"]
                    if pend_rm.get("tp"):
                        st.session_state["ord_tp"] = pend_rm["tp"]

            # --- One-Click Trading (interruptor a la derecha) ---
            with st.container(key="ord_tg_oc"):
                oc = st.toggle("One-Click Trading", key="ord_oc", on_change=_oc_cambiar,
                               help="Activo: las órdenes del ticket y del gráfico se envían sin "
                                    "confirmación. La primera vez pide aceptar los términos.")
            pedir_terminos_si_corresponde()

            # --- VENTA | COMPRA unidos + spread (selección por mitades) ---
            pip = (point * 10) if dig in (3, 5) else (point or 1)
            spr_val = (ask - bid) / pip if pip else 0
            spr = f"{spr_val:,.1f}" if spr_val < 100 else f"{spr_val:,.0f}"
            with st.container(key="ord_bxrow"):
                st.html(
                    "<div class='ord-join'>"
                    f"<div class='ord-half ord-sell {'' if compra else 'sel'}'><div class='ord-lbl'>SELL</div>"
                    f"<div class='ord-px' {_live(real, 'bid', d=dig)}>{bid:,.{dig}f}</div></div>"
                    f"<div class='ord-half ord-buy {'sel' if compra else ''}'><div class='ord-lbl'>BUY</div>"
                    f"<div class='ord-px' {_live(real, 'ask', d=dig)}>{ask:,.{dig}f}</div></div>"
                    f"<div class='ord-spread' {_live(real, 'spr', pip=pip)}>{spr}</div>"
                    "</div>"
                )
                if st.button("Vender", key="ord_ovsell"):
                    st.session_state.ord_side = "SELL"
                    st.rerun(scope="fragment")
                if st.button("Comprar", key="ord_ovbuy"):
                    st.session_state.ord_side = "BUY"
                    st.rerun(scope="fragment")

            # --- Cantidad | Lotes + volumen (tarjeta con número grande) ---
            contract = float(getattr(info, "trade_contract_size", 1) or 1)
            modo = st.segmented_control("Tipo de volumen", ["Cantidad", "Lotes"], default="Lotes",
                                        label_visibility="collapsed", key="ord_modo",
                                        width="stretch") or "Lotes"
            if modo == "Lotes":
                with _campo("qty", "Volumen", "lote(s)"):
                    vol = st.number_input("Volumen (lotes)", min_value=vmin, value=vmin,
                                          step=vstep, format="%.2f", key="ord_vol",
                                          label_visibility="collapsed")
            else:
                with _campo("qty", "Cantidad", "unidades"):
                    cant = st.number_input("Cantidad (unidades)", min_value=1.0, value=1.0,
                                           step=1.0, format="%.0f", key="ord_cant",
                                           label_visibility="collapsed")
                vol = (cant / contract) if contract else cant
                vol = max(vmin, round(vol / vstep) * vstep) if vstep else max(vmin, vol)

            # Hueco del margen ANTES de la orden pendiente (orden visual de XM);
            # se llena más abajo porque depende del precio pendiente.
            slot_margen = st.container()

            # --- Pending order: Buy/Sell Limit o Stop según el precio pedido ---
            ref = ask if compra else bid
            pendiente, gtc = None, True
            oco_on, oco_lado_b, oco_precio_b, oco_tipo_b = False, None, None, ""
            with st.container(key="ord_card_pend"):
                with st.container(key="ord_tg_pend"):
                    usar_pend = st.toggle(
                        "Pending order", key="ord_pend",
                        help=("Se ejecuta cuando el mercado llega al precio indicado: "
                              + ("Buy Limit bajo el precio actual, Buy Stop sobre él." if compra
                                 else "Sell Limit sobre el precio actual, Sell Stop bajo él.")))
                if usar_pend:
                    with _campo("pxp", "Precio"):
                        pendiente = st.number_input(
                            "Precio de la orden pendiente", min_value=0.0, value=round(float(ref), dig),
                            step=(point * 10) or 0.0001, format=f"%.{dig}f",
                            key=f"ord_pxp_{real}_{side}", label_visibility="collapsed")
                    if compra:
                        tipo_pend = "Buy Limit" if pendiente < ref else "Buy Stop"
                    else:
                        tipo_pend = "Sell Limit" if pendiente > ref else "Sell Stop"
                    st.html(f"<div class='ord-hint'>Precio actual ({'Ask' if compra else 'Bid'}):"
                            f"<b {_live(real, 'side', d=dig, side=side)}>{ref:,.{dig}f}</b></div>"
                            f"<div class='ord-hint'>Tipo de orden:<b>{tipo_pend}</b></div>"
                            "<div class='ord-sep'></div>")
                    with st.container(key="ord_tg_gtc"):
                        gtc = st.toggle("Good till cancelled (GTC)", value=True, key="ord_gtc",
                                        help="Apagado: DAY, la orden vence al final del día.")

                    # --- OCO: segunda orden vinculada (One-Cancels-the-Other) ---
                    st.html("<div class='ord-sep'></div>")
                    with st.container(key="ord_tg_oco"):
                        oco_on = st.toggle(
                            "OCO (One-Cancels-the-Other)", key="ord_oco_tg",
                            help="Coloca DOS órdenes pendientes vinculadas: cuando una se ejecuta, "
                                 "la otra se cancela sola. Típico para un breakout (Buy Stop arriba + "
                                 "Sell Stop abajo). Necesita el servidor de datos en marcha.")
                    if oco_on:
                        st.html("<div class='ord-sub' style='margin-top:2px'>Segunda orden del par</div>")
                        lb = st.segmented_control(
                            "Lado de la segunda orden", ["Compra", "Venta"],
                            default=("Venta" if compra else "Compra"), label_visibility="collapsed",
                            key="ord_oco_lado", width="stretch") or ("Venta" if compra else "Compra")
                        oco_lado_b = "BUY" if lb == "Compra" else "SELL"
                        refb = ask if oco_lado_b == "BUY" else bid
                        with _campo("pxb", "Segundo precio"):
                            oco_precio_b = st.number_input(
                                "Precio de la segunda orden", min_value=0.0,
                                value=round(float(refb), dig), step=(point * 10) or 0.0001,
                                format=f"%.{dig}f", key=f"ord_pxb_{real}_{side}",
                                label_visibility="collapsed")
                        if oco_lado_b == "BUY":
                            oco_tipo_b = "Buy Limit" if oco_precio_b < refb else "Buy Stop"
                        else:
                            oco_tipo_b = "Sell Limit" if oco_precio_b > refb else "Sell Stop"
                        st.html(
                            f"<div class='ord-hint'>Orden A (esta):"
                            f"<b>{tipo_pend} · {'BUY' if compra else 'SELL'} @ {pendiente:,.{dig}f}</b></div>"
                            f"<div class='ord-hint'>Orden B:"
                            f"<b>{oco_tipo_b} · {oco_lado_b} @ {oco_precio_b:,.{dig}f}</b></div>"
                            "<div class='ord-hint' style='margin-top:4px;color:#8b949e'>El Stop Loss / "
                            "Take Profit se define sobre la posición cuando una pata se ejecute.</div>")

            # --- Margen requerido + % del margen libre (como XM) ---
            price = pendiente if pendiente else ref
            m = _margen(real, vol, price, side)
            libre = _margen_libre()
            sin_margen = bool(m and libre is not None and m > libre)
            if m:
                pct = (m / libre * 100) if libre and libre > 0 else 100.0
                color = "#f85149" if sin_margen else ("#d29922" if pct >= 90 else "#2f81f7")
                slot_margen.html(
                    f"<div class='ord-margen'><span>Margen requerido</span><b>${m:,.2f}</b></div>"
                    f"<div class='ord-mbar-row'><div class='ord-mbar'>"
                    f"<div style='width:{min(pct, 100):.1f}%; background:{color};'></div></div>"
                    f"<span class='ord-mbar-pct' style='color:{color if sin_margen else '#e6edf3'};'>"
                    f"{pct:,.2f}%</span></div>"
                    + ("<div class='ord-sin-margen'>No tiene margen suficiente para colocar "
                       "esta orden.</div><style>.st-key-ord_box_qty [data-testid='stNumberInputContainer'] "
                       "{ border-color:#f85149 !important; box-shadow:0 0 0 1px #f85149 !important; }"
                       "</style>" if sin_margen else "")
                )

            # --- Take Profit / Stop Loss (no aplica en OCO: patas en lados opuestos) ---
            sl = tp = 0.0
            if not oco_on:
                with st.container(key="ord_card_tpsl"):
                    with st.container(key="ord_tg_tpsl"):
                        usar_tpsl = st.toggle("Take Profit / Stop Loss", key="ord_tpsl")
                    if usar_tpsl:
                        with _campo("sl", "Stop Loss"):
                            sl = st.number_input("Stop Loss", min_value=0.0, value=0.0,
                                                 step=point or 0.0001, format=f"%.{dig}f",
                                                 key="ord_sl", label_visibility="collapsed")
                        with _campo("tp", "Take Profit"):
                            tp = st.number_input("Take Profit", min_value=0.0, value=0.0,
                                                 step=point or 0.0001, format=f"%.{dig}f",
                                                 key="ord_tp", label_visibility="collapsed")

            # --- Calculadora de riesgo (Risk Manager): tamaño por riesgo + TP por R/R ---
            with st.container(key="ord_card_rm"):
                with st.container(key="ord_tg_rm"):
                    usar_rm = st.toggle(
                        "Calculadora de riesgo", key="ord_rm",
                        help="Sugiere cuántos lotes operar para no arriesgar más de un % de tu "
                             "capital, y el Take Profit por relación riesgo/beneficio (R/R). "
                             "'Aplicar' rellena volumen, Stop Loss y Take Profit en el ticket.")
                if usar_rm:
                    tsize = float(getattr(info, "trade_tick_size", 0) or 0) if info else 0.0
                    tval = float(getattr(info, "trade_tick_value", 0) or 0) if info else 0.0
                    kval = (tval / tsize) if tsize else 0.0        # valor de 1 unidad de precio por lote
                    contract = float(getattr(info, "trade_contract_size", 1) or 1) if info else 1.0
                    vmax = float(getattr(info, "volume_max", 100) or 100) if info else 100.0
                    equity, moneda = _capital_cuenta()
                    with _campo("rmcap", "Capital", moneda):
                        cap = st.number_input("Capital", min_value=0.0,
                                              value=float(round(equity or 0.0, 2)), step=100.0,
                                              format="%.2f", key="ord_rm_cap", label_visibility="collapsed")
                    modo_r = st.segmented_control("Riesgo en", ["%", moneda], default="%",
                                                  label_visibility="collapsed", key="ord_rm_modo",
                                                  width="stretch") or "%"
                    if modo_r == "%":
                        with _campo("rmpct", "Riesgo por operación", "%"):
                            rpct = st.number_input("Riesgo %", min_value=0.0, max_value=100.0, value=1.0,
                                                   step=0.25, format="%.2f", key="ord_rm_pct",
                                                   label_visibility="collapsed")
                        riesgo = cap * rpct / 100.0
                    else:
                        with _campo("rmusd", "Riesgo por operación", moneda):
                            riesgo = st.number_input("Riesgo", min_value=0.0,
                                                     value=float(round((cap or 0.0) * 0.01, 2)), step=50.0,
                                                     format="%.2f", key="ord_rm_usd",
                                                     label_visibility="collapsed")
                    with _campo("rment", "Entrada"):
                        entrada = st.number_input("Entrada", min_value=0.0,
                                                  value=float(round(price, dig)),
                                                  step=(point * 10) or 0.0001, format=f"%.{dig}f",
                                                  key=f"ord_rm_ent_{real}_{side}", label_visibility="collapsed")
                    with _campo("rmstop", "Stop Loss"):
                        stop_rm = st.number_input("Stop", min_value=0.0, value=0.0,
                                                  step=(point * 10) or 0.0001, format=f"%.{dig}f",
                                                  key=f"ord_rm_stop_{real}_{side}", label_visibility="collapsed")
                    with _campo("rmrr", "R/R objetivo", ": 1"):
                        rr = st.number_input("R/R", min_value=0.1, value=2.0, step=0.5, format="%.1f",
                                             key="ord_rm_rr", label_visibility="collapsed")
                    dist = abs(entrada - stop_rm) if (entrada > 0 and stop_rm > 0) else 0.0
                    lado_ok = (stop_rm < entrada) if compra else (stop_rm > entrada)
                    msg = ""
                    if kval <= 0:
                        msg = "Este símbolo no entrega el valor por punto; no se puede calcular."
                    elif entrada <= 0 or stop_rm <= 0:
                        msg = "Indica la Entrada y el Stop para calcular el tamaño."
                    elif not lado_ok:
                        msg = ("En una compra el Stop va bajo la entrada." if compra
                               else "En una venta el Stop va sobre la entrada.")
                    elif dist <= 0 or riesgo <= 0:
                        msg = "Indica un riesgo y una distancia de stop válidos."
                    if msg:
                        st.html(f"<div class='ord-hint' style='color:#8b949e'>{msg}</div>")
                    else:
                        perd_lote = dist * kval
                        lotes_raw = riesgo / perd_lote if perd_lote else 0.0
                        lotes = max(vmin, round(lotes_raw / vstep) * vstep) if vstep else max(vmin, lotes_raw)
                        lotes = round(min(lotes, vmax), 2)
                        perd_real = lotes * dist * kval
                        tp_sug = round(entrada + (rr * dist) * (1 if compra else -1), dig)
                        gan = lotes * (rr * dist) * kval
                        unidades = lotes * contract
                        m_rm = _margen(real, lotes, entrada, side)
                        riesgo_bajo = lotes_raw < vmin
                        st.html(
                            "<div class='ord-sep'></div>"
                            f"<div class='ord-margen'><span>Riesgo máximo</span>"
                            f"<b>{riesgo:,.2f} {moneda}</b></div>"
                            f"<div class='ord-margen'><span>Tamaño recomendado</span>"
                            f"<b>{lotes:,.2f} lote(s) · {unidades:,.0f} u.</b></div>"
                            f"<div class='ord-margen'><span>Pérdida al stop</span>"
                            f"<b style='color:#f85149'>-{perd_real:,.2f} {moneda}</b></div>"
                            f"<div class='ord-margen'><span>Take Profit ({rr:.1f}:1)</span>"
                            f"<b>{tp_sug:,.{dig}f}</b></div>"
                            f"<div class='ord-margen'><span>Ganancia potencial</span>"
                            f"<b style='color:#3fb950'>+{gan:,.2f} {moneda}</b></div>"
                            + (f"<div class='ord-margen'><span>Margen requerido</span>"
                               f"<b>{m_rm:,.2f} {moneda}</b></div>" if m_rm else "")
                            + (f"<div class='ord-hint' style='color:#d29922;margin-top:4px'>El riesgo "
                               f"elegido es menor al lote mínimo ({vmin:g}); con {vmin:g} lote(s) la "
                               f"pérdida sería {vmin * dist * kval:,.2f} {moneda}.</div>" if riesgo_bajo else "")
                        )
                        if st.button("Aplicar al ticket", key="ord_rm_aplicar", width="stretch",
                                     icon=":material/check:"):
                            st.session_state._rm_aplicar = {
                                "vol": lotes,
                                "sl": None if oco_on else round(stop_rm, dig),
                                "tp": None if oco_on else tp_sug,
                            }
                            st.rerun(scope="fragment")

            # --- Botón grande "Colocar orden en {precio}" (o "Colocar OCO") ---
            es_oco = bool(oco_on and pendiente and oco_precio_b)
            # OCO inválido: mismas patas (igual lado y prácticamente igual precio)
            oco_malo = bool(es_oco and oco_lado_b == ("BUY" if compra else "SELL")
                            and abs(oco_precio_b - pendiente) < (point or 1e-9))
            off = sin_margen or oco_malo
            cls = ("ord-place-buy" if compra else "ord-place-sell") + (" ord-place-off" if off else "")
            if es_oco:
                pl_lbl, pl_px, px_attr, px_style = "Colocar OCO · 2 órdenes", \
                    f"{pendiente:,.{dig}f} / {oco_precio_b:,.{dig}f}", "", "font-size:15px"
            else:
                # Pendiente: precio fijo elegido; a mercado: precio en vivo (feed)
                pl_lbl, pl_px, px_style = "Colocar orden en", f"{price:,.{dig}f}", ""
                px_attr = "" if pendiente else _live(real, "side", d=dig, side=side)
            with st.container(key="ord_bxplace"):
                st.html(
                    f"<div class='ord-place {cls}'>"
                    f"<div><div class='pl-lbl'>{pl_lbl}</div>"
                    f"<div class='pl-px' style='{px_style}' {px_attr}>{pl_px}</div></div>"
                    f"<div class='pl-arrow'>{'↗' if compra else '↘'}</div></div>"
                )
                if not off and st.button("Colocar orden", key="ord_ovplace"):
                    st.session_state.pop("ord_result", None)  # limpia resultado previo
                    st.session_state.ord_confirm = None
                    st.session_state.ord_oco_confirm = None
                    lado = "BUY" if compra else "SELL"
                    if es_oco:
                        if oc:
                            _ejecutar_oco(real, visible, lado, oco_lado_b,
                                          pendiente, oco_precio_b, vol, gtc)
                            st.rerun(scope="fragment")
                        else:
                            st.session_state.ord_oco_confirm = {
                                "real": real, "visible": visible, "dig": dig, "ladoA": lado,
                                "ladoB": oco_lado_b, "pa": pendiente, "pb": oco_precio_b,
                                "vol": vol, "gtc": gtc, "ta": tipo_pend, "tb": oco_tipo_b}
                            st.rerun(scope="fragment")   # instantáneo (sin recargar el gráfico)
                    elif oc:
                        _ejecutar(real, visible, side, vol, sl, tp, pendiente, gtc)
                        st.rerun(scope="fragment")
                    else:
                        st.session_state.ord_confirm = {
                            "real": real, "visible": visible, "dig": dig, "side": side,
                            "vol": vol, "sl": sl, "tp": tp, "price": price,
                            "pend": pendiente, "gtc": gtc}
                        st.rerun(scope="fragment")   # instantáneo (sin recargar el gráfico)

            # --- Confirmación (tarjeta flotante abajo-derecha, formato naranja como el
            #     cierre de Cartera). Inline en el fragmento → aparece al instante, sin
            #     oscurecer la pantalla ni recargar el gráfico. ---
            _render_confirmacion()

            # --- Aviso del resultado: toast naranja (éxito) / rojo (error), se cierra
            #     solo (~6 s) o con la ✕. Se inyecta en el documento padre una sola vez
            #     por resultado (el nonce evita que se repita en cada refresco). ---
            r = st.session_state.get("ord_result")
            if r:
                with st.container(key="ord_toastjs"):
                    _msg = r[1] if r[0] == "ok" else f"No se pudo operar: {r[1]}"
                    components.html(
                        _toast_js(_msg, r[0] != "ok",
                                  st.session_state.get("ord_result_nonce", "0")),
                        height=0)

        _ticket()
