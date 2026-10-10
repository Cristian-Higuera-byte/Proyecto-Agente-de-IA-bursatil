"""
panel_rail.py
-------------
Rail de iconos FIJO a la derecha (estilo XM), gemelo de la barra lateral izquierda
(components/nav_bar.py), pero debajo de la barra superior. Cada icono despliega /
oculta su panel.

Rendimiento: el toggle NO reejecuta Python (como el ☰ del nav izquierdo). Los
paneles (Operar, DOM) se dibujan SIEMPRE; un script intercepta el clic del icono
(antes de que llegue a Streamlit) y alterna clases en <html>; el CSS desliza el
panel y reserva el espacio a la derecha → aparece al instante, sin recargar el
gráfico (es autoSize, solo se reajusta).

Estados (clase en <html>):
  - (sin clase)      → Operar abierto (DEFAULT: al entrar o F5 el ticket está visible)
  - pj-panel-dom     → DOM abierto (Operar oculto)
  - pj-panel-none    → todo oculto (gráfico a pantalla completa)
Así, tras un F5 (ventana nueva, sin clases) el ticket queda desplegado; el usuario
lo oculta con su botón. El estado se mantiene al navegar entre vistas (la clase
vive en <html>), solo se reinicia con F5.

Tooltip: en vez del `help` de Streamlit (que en un contenedor fijo se queda
pegado), el nombre se muestra con un tooltip CSS propio (::after) al pasar el mouse.
"""
import json
import streamlit as st
import streamlit.components.v1 as components

RAIL = 50        # ancho del rail (px) — angosto, como una barra de iconos
PANEL = 312      # ancho del panel desplegado (px)
TOP = 62         # alto de la barra superior (ajústalo si el panel queda alto/bajo)

# (icono material, id del panel, nombre del tooltip)
BOTONES = [
    (":material/swap_vert:", "order", "Operar"),
    (":material/reorder:", "dom", "Profundidad de mercado (DOM)"),
]

_JS = """
<script>
(function(){
  var P = window.parent, D, H;
  try { D = P.document; H = D.documentElement; } catch(e) { return; }
  function estado(){
    if (H.classList.contains('pj-panel-dom')) return 'dom';
    if (H.classList.contains('pj-panel-none')) return 'none';
    return 'order';   // sin clase = Operar abierto (default al entrar / F5)
  }
  function poner(s){
    H.classList.toggle('pj-panel-dom', s === 'dom');
    H.classList.toggle('pj-panel-none', s === 'none');
  }
  if (P.__pjRailFn) D.removeEventListener('click', P.__pjRailFn, true);
  P.__pjRailFn = function(e){
    if (!(e.target && e.target.closest)) return;
    var bo = e.target.closest('.st-key-rail_order button');
    var bd = e.target.closest('.st-key-rail_dom button');
    if (!bo && !bd) return;
    e.stopPropagation(); e.preventDefault();
    var c = estado();
    if (bo) poner(c === 'order' ? 'none' : 'order');
    else    poner(c === 'dom' ? 'none' : 'dom');
  };
  D.addEventListener('click', P.__pjRailFn, true);
})();
</script>
"""


def _css() -> str:
    tips = "\n".join(
        f'    .st-key-rail_{pid} button::after {{ content: {json.dumps(nom)}; }}'
        for _, pid, nom in BOTONES
    )
    return f"""
<style>
    /* El contenido reserva a la derecha el rail + el panel. Operar abierto por
       defecto y DOM abierto reservan rail+panel; solo "none" reserva únicamente el rail.
       (El gráfico es autoSize: se reajusta sin recargar el iframe.) */
    .block-container {{ padding-right: {RAIL + PANEL + 16}px !important;
        transition: padding-right .2s ease; }}
    html.pj-panel-none .block-container {{ padding-right: {RAIL + 16}px !important; }}

    /* ===== Rail FIJO a la derecha, debajo de la barra superior ===== */
    .st-key-pj_rail {{
        position: fixed !important; right: 0 !important; top: {TOP}px !important;
        height: calc(100vh - {TOP}px) !important; width: {RAIL}px !important;
        background: #0d1117; border-left: 1px solid #30363d;
        padding: 12px 2px !important; box-sizing: border-box; z-index: 100000;
        overflow: visible;   /* deja ver el tooltip, que sale a la izquierda */
    }}
    .st-key-pj_rail [data-testid="stVerticalBlock"] {{ gap: 6px !important; align-items: center; }}
    /* Botones por su key propia (como el nav izquierdo): solo el ícono, sin caja */
    [class*="st-key-rail_"] div.stButton > button, [class*="st-key-rail_"] button {{
        background: transparent !important; border: none !important; box-shadow: none !important;
        color: #8b949e !important; width: 44px !important; height: 44px !important;
        min-height: 44px !important; padding: 0 !important; border-radius: 10px !important;
        margin: 0 !important; position: relative;
        transition: background-color .15s ease, color .15s ease !important;
    }}
    [class*="st-key-rail_"] button p {{ font-size: 24px !important; line-height: 1 !important; }}
    [class*="st-key-rail_"] button:hover {{ background: rgba(255,255,255,0.08) !important;
        color: #fff !important; }}

    /* Tooltip propio (nombre del panel) a la izquierda, solo al pasar el mouse */
    [class*="st-key-rail_"] button::after {{
        position: absolute; right: calc(100% + 8px); top: 50%; transform: translateY(-50%);
        background: #161b22; border: 1px solid #30363d; color: #e6edf3;
        font-size: 12px; font-weight: 600; padding: 4px 9px; border-radius: 6px;
        white-space: nowrap; opacity: 0; pointer-events: none;
        transition: opacity .12s ease; z-index: 100002;
    }}
    [class*="st-key-rail_"] button:hover::after {{ opacity: 1; }}
{tips}

    /* Icono del panel abierto en verde (como el nav izquierdo activo).
       Operar está activo salvo que haya DOM o todo oculto. */
    html:not(.pj-panel-dom):not(.pj-panel-none) .st-key-rail_order button {{
        background: rgba(34,197,94,0.12) !important; color: #22c55e !important;
    }}
    html.pj-panel-dom .st-key-rail_dom button {{
        background: rgba(34,197,94,0.12) !important; color: #22c55e !important;
    }}

    /* ===== Paneles FIJOS (se deslizan fuera de pantalla al ocultarse) ===== */
    .st-key-pj_panel_order, .st-key-pj_panel_dom {{
        position: fixed !important; right: {RAIL}px !important; top: {TOP}px !important;
        height: calc(100vh - {TOP}px) !important; width: {PANEL}px !important;
        background: #0b0f19; border-left: 1px solid #30363d; z-index: 99999;
        overflow-y: auto; overflow-x: hidden; padding: 12px 10px !important;
        box-sizing: border-box; transition: transform .2s ease;
    }}
    /* Operar: visible por defecto; oculto con DOM o con "none" */
    .st-key-pj_panel_order {{ transform: translateX(0); }}
    html.pj-panel-dom .st-key-pj_panel_order,
    html.pj-panel-none .st-key-pj_panel_order {{ transform: translateX(110%); }}
    /* DOM: oculto por defecto; visible solo con pj-panel-dom */
    .st-key-pj_panel_dom {{ transform: translateX(110%); }}
    html.pj-panel-dom .st-key-pj_panel_dom {{ transform: translateX(0); }}
    .st-key-pj_panel_order [data-testid="stVerticalBlockBorderWrapper"],
    .st-key-pj_panel_dom [data-testid="stVerticalBlockBorderWrapper"] {{ background: transparent; }}

    /* Script del rail: fuera del flujo */
    .st-key-pj_railjs {{ position: absolute !important; width: 0 !important;
        height: 0 !important; overflow: hidden !important; }}
</style>
"""


def inyectar_css_rail():
    """Inyecta el CSS del rail. Debe llamarse ANTES de dibujar el gráfico, para que
    éste se mida con el espacio ya reservado a la derecha (si no, queda recortado)."""
    st.markdown(_css(), unsafe_allow_html=True)


def renderizar_rail_y_paneles(main=None):
    # Paneles: se dibujan SIEMPRE (el CSS muestra el activo y oculta el resto).
    with st.container(key="pj_panel_order"):
        from components.order_panel import renderizar_panel_orden
        renderizar_panel_orden(main)
    with st.container(key="pj_panel_dom"):
        from components.dom_panel import renderizar_panel_dom
        renderizar_panel_dom()

    # Rail de iconos (mismo estilo que el nav izquierdo: solo el ícono).
    with st.container(key="pj_rail"):
        for icono, pid, _nom in BOTONES:
            st.button(icono, key=f"rail_{pid}")

    # Script que alterna los paneles sin reejecutar Python.
    with st.container(key="pj_railjs"):
        components.html(_JS, height=0)
