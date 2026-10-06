"""
one_click.py
------------
Modo "One-Click Trading" (como MT5): con el interruptor activo, las órdenes del
ticket, del menú del clic derecho del gráfico y los arrastres de líneas
(Buy/Sell Limit/Stop, Take Profit, Stop Loss) se envían SIN confirmación.

La PRIMERA vez que un usuario lo activa debe aceptar la renuncia de
responsabilidades (modal). La aceptación queda registrada en el servidor, con
fecha, en `data/one_click_aceptaciones.json` (ignorado por git) y no se vuelve a
pedir. El interruptor vive en el ticket de órdenes (clave `ord_oc`); el gráfico
lee su estado del DOM y, para activarlo desde el menú, pulsa ese mismo interruptor.

Uso:
- order_panel.py: `st.toggle(..., key="ord_oc", on_change=al_cambiar)`
- app.py: `render_modal_terminos()` (fuera de los fragmentos en vivo)
"""
import json
import os
from datetime import datetime

import streamlit as st

# MODO DEMO: la renuncia se muestra CADA VEZ que se activa One-Click Trading (para
# presentaciones). La aceptación se sigue registrando en _RUTA con su fecha.
# Para el uso normal (pedirla solo la primera vez), poner False.
PEDIR_SIEMPRE = True

_RUTA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "data", "one_click_aceptaciones.json")


def _uid() -> str:
    u = st.session_state.get("usuario_info") or {}
    return str(u.get("id") or u.get("email") or "anonimo")


def _leer() -> dict:
    try:
        with open(_RUTA, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def aceptado() -> bool:
    """¿El usuario actual ya aceptó los términos de One-Click Trading?"""
    if PEDIR_SIEMPRE:
        return False
    if st.session_state.get("oct_aceptado"):
        return True
    ok = _uid() in _leer()
    if ok:
        st.session_state.oct_aceptado = True
    return ok


def _registrar():
    datos = _leer()
    u = st.session_state.get("usuario_info") or {}
    datos[_uid()] = {"email": u.get("email", ""), "fecha": datetime.now().isoformat(timespec="seconds"),
                     "version_terminos": 1}
    os.makedirs(os.path.dirname(_RUTA), exist_ok=True)
    with open(_RUTA, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    st.session_state.oct_aceptado = True


def al_cambiar():
    """on_change del interruptor: si se activa sin haber aceptado, se apaga y se
    pide aceptar los términos (el modal lo abre app.py en el rerun completo)."""
    if st.session_state.get("ord_oc") and not aceptado():
        st.session_state.ord_oc = False
        st.session_state.oct_terminos = True
        st.session_state._oct_pedir = True     # una sola vez: rerun de app para abrir el modal


def pedir_terminos_si_corresponde():
    """Llamar dentro del fragmento del ticket, tras el interruptor: si hay que
    mostrar los términos, rerun de la app (el modal se dibuja fuera del fragmento)."""
    if st.session_state.pop("_oct_pedir", False):
        st.rerun(scope="app")


def _aceptar():
    _registrar()
    st.session_state.ord_oc = True
    st.session_state.oct_terminos = False


def _cancelar():
    st.session_state.oct_terminos = False


_TEXTO = """
<div class='oct-txt'>
<p class='oct-c'>Renuncia de responsabilidades</p>
<p>Está a punto de activar el modo <b>One-Click Trading</b> de la plataforma de trading de
Piña y Jara. Al hacer clic en <b>"Acepto los Términos y Condiciones"</b> usted confirma que ha
leído, comprendido y aceptado lo que se indica a continuación.</p>

<p><b>1. Modo estándar (por defecto).</b> Cada operación requiere dos pasos: primero se prepara
la orden (ticket de órdenes, menú del gráfico o arrastre de una línea) y luego se confirma
explícitamente. La orden no se envía al bróker hasta completar ambos pasos.</p>

<p><b>2. Modo One-Click Trading.</b> La orden se envía al bróker <b>de inmediato, en un solo
paso</b>, sin pedir confirmación, al:</p>
<ul>
<li>pulsar "Colocar orden" en el ticket de órdenes;</li>
<li>elegir <b>Buy Limit, Sell Limit, Buy Stop o Sell Stop</b> en el menú del clic derecho del gráfico;</li>
<li>arrastrar en el gráfico el precio de una orden pendiente o sus niveles de
<b>Take Profit / Stop Loss</b>, o los de una posición abierta;</li>
<li>quitar un Take Profit / Stop Loss o cancelar una orden pendiente desde el gráfico.</li>
</ul>

<p class='oct-may'>NO SE LE PEDIRÁ CONFIRMAR LA OPERACIÓN. UNA VEZ ENVIADA, LA ORDEN SE EJECUTARÁ
SEGÚN LAS CONDICIONES DEL MERCADO Y NO PODRÁ CANCELARSE NI MODIFICARSE A POSTERIORI EN ESE ENVÍO.</p>

<p><b>3.</b> Puede activar o desactivar este modo cuando quiera con el interruptor
"One-Click Trading" del ticket de órdenes o desde el menú del clic derecho del gráfico.</p>

<p><b>4.</b> Al activar este modo usted acepta todos los riesgos asociados al envío inmediato de
órdenes, incluidos los errores de operación (por ejemplo, un clic o un arrastre involuntario),
y libera a Piña y Jara Transportes y Servicios LTDA. de los daños, pérdidas o gastos que
pudieran derivarse de dichos errores, cometidos por usted o por cualquier persona que opere
con su cuenta.</p>

<p class='oct-nota'>La aceptación queda registrada con su usuario y la fecha.</p>
</div>
"""

_CSS = """
<style>
  [data-testid="stDialog"]:has(.st-key-oct_root) section {
      background:#0d1117 !important; border:1px solid #30363d; border-radius:16px; }
  .oct-txt { max-height:52vh; overflow-y:auto; padding:4px 14px 4px 2px; color:#c9d1d9;
             font-size:13.5px; line-height:1.55; text-align:justify; }
  .oct-txt p { margin:0 0 12px; }
  .oct-txt ul { margin:-4px 0 12px 18px; padding:0; }
  .oct-txt li { margin:2px 0; }
  .oct-c { text-align:center; font-weight:700; color:#e6edf3; font-size:14.5px; }
  .oct-may { color:#e6edf3; font-weight:600; background:#161b22; border-left:3px solid #ff8f00;
             padding:9px 12px; border-radius:6px; }
  .oct-nota { color:#8b949e; font-size:12px; }
  .st-key-oct_ok button { background:linear-gradient(90deg,#ff4b4b,#ff8f00) !important;
      border:none !important; color:#fff !important; font-weight:700; }
</style>
"""


@st.dialog("One-Click Trading", width="large", on_dismiss=_cancelar)
def _dialogo():
    with st.container(key="oct_root"):
        st.html(_CSS)
        st.html(_TEXTO)
        c1, c2 = st.columns([1, 1.4])
        with c1:
            if st.button("Cancelar", key="oct_cancel", width="stretch", on_click=_cancelar):
                st.rerun()
        with c2:
            with st.container(key="oct_ok"):
                if st.button("Acepto los Términos y Condiciones", key="oct_ok_btn",
                             width="stretch", on_click=_aceptar):
                    st.toast("One-Click Trading activado.", icon=":material/bolt:")
                    st.rerun()


def render_modal_terminos():
    """Llamar desde app.py (fuera de los fragmentos en vivo)."""
    if st.session_state.get("oct_terminos"):
        _dialogo()
