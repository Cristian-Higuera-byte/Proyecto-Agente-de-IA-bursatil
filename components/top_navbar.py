"""
top_navbar.py
-------------
Barra de navegación superior del dashboard (estilo terminal de trading).
- Buscador (visual por ahora) en la posición del antiguo logo.
- Íconos de tema y campana de notificaciones (core/notificaciones.py): avisa cuando el agente
  termina de responder aunque el usuario esté en otra sección.
- Usuario a la derecha: al hacer clic en el nombre se despliega un menú
  (perfil / configuración / cerrar sesión) — con <details>, sin recargar.

La barra queda FIJA arriba y a todo el ancho gracias al contenedor
`st.container(key="barra_nav_fija")` de app.py + su CSS (position: fixed).
"""
import html
import time

import streamlit as st

from components.buscador import abrir_buscador
from core import notificaciones

# --- Íconos de línea (estilo Lucide/Feather), heredan color con currentColor ---
_IC_BUSCAR = (
    "<svg width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='currentColor' "
    "stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
    "<circle cx='11' cy='11' r='8'/><path d='m21 21-4.3-4.3'/></svg>"
)
_IC_TEMA = (
    "<svg width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='currentColor' "
    "stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
    "<path d='M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z'/></svg>"
)
_IC_NOTIF = (
    "<svg width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='currentColor' "
    "stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
    "<path d='M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9'/>"
    "<path d='M10.3 21a1.94 1.94 0 0 0 3.4 0'/></svg>"
)

_ICONO_TIPO = {"agente": "🤖", "orden": "📋", "error": "⚠️"}


def _usuario_id() -> str:
    return str((st.session_state.get("usuario_info") or {}).get("id") or "local")


def _hace(creada: float) -> str:
    seg = max(0, int(time.time() - creada))
    if seg < 60:
        return "ahora"
    if seg < 3600:
        return f"hace {seg // 60} min"
    if seg < 86400:
        return f"hace {seg // 3600} h"
    return f"hace {seg // 86400} d"


def _html_notificaciones(items: list) -> str:
    if not items:
        return ("<div class='nt-vacio'>Sin notificaciones por ahora. Aquí te avisamos cuando el agente "
                "termine de responder.</div>")
    filas = []
    for n in items:
        punto = "" if n["leida"] else "<span class='nt-punto'></span>"
        filas.append(
            f"<div class='nt-item{'' if n['leida'] else ' nueva'}'>"
            f"<div class='nt-ic'>{_ICONO_TIPO.get(n['tipo'], '🔔')}</div>"
            f"<div class='nt-cuerpo'><div class='nt-titulo'>{html.escape(n['titulo'])}{punto}</div>"
            f"<div class='nt-texto'>{html.escape(n['texto'])}</div>"
            f"<div class='nt-hace'>{_hace(n['creada'])}</div></div></div>"
        )
    return "".join(filas)


@st.fragment(run_every="3s")
def _vigilar_notificaciones(usuario_id: str) -> None:
    """Revisa cada 3 s (sin dibujar nada) si llegó un aviso nuevo. Solo entonces refresca la app,
    para que aparezcan la insignia y el toast aunque el usuario esté en otra sección."""
    if notificaciones.ultima_id(usuario_id) != st.session_state.get("_notif_ultima_id"):
        st.rerun(scope="app")


def _campana(usuario_id: str) -> None:
    """Campana con insignia + lista desplegable (popover de Streamlit: sus botones son reales)."""
    st.session_state["_notif_ultima_id"] = notificaciones.ultima_id(usuario_id)
    items = notificaciones.listar(usuario_id, 8)
    sin_leer = notificaciones.no_leidas(usuario_id)

    # Aviso emergente, una sola vez por notificación y sesión.
    vistas = st.session_state.setdefault("_notif_toast", set())
    for n in reversed(items):
        if not n["leida"] and n["id"] not in vistas:
            vistas.add(n["id"])
            st.toast(f"**{n['titulo']}**\n\n{n['texto']}", icon=_ICONO_TIPO.get(n["tipo"], "🔔"))

    with st.container(key="notif_bell"):
        if sin_leer:
            st.html(f"<span class='nt-badge'>{sin_leer if sin_leer < 10 else '9+'}</span>")
        with st.popover("", icon=":material/notifications:"):
            st.html(
                "<div class='nt-cab'>Notificaciones"
                + (f"<span class='nt-cuenta'>{sin_leer} nueva{'s' if sin_leer != 1 else ''}</span>" if sin_leer else "")
                + "</div>"
            )
            st.html(_html_notificaciones(items))
            if items:
                if st.button("Ver el chat del agente", key="notif_ir", icon=":material/chat:", type="primary",
                             width="stretch"):
                    notificaciones.marcar_leidas(usuario_id)
                    st.session_state.nav_activo = "trading"
                    st.rerun()
                # Marcar como leídas = ya las viste: se eliminan de la lista (y desaparece la insignia).
                if st.button("Marcar como leídas", key="notif_leer", icon=":material/done_all:", width="stretch"):
                    notificaciones.limpiar(usuario_id)
                    st.rerun()
    _vigilar_notificaciones(usuario_id)


def renderizar_barra_navegacion(usuario: str = "Emilio Fuentes",
                                saldo: float | None = None,
                                moneda: str = "USD",
                                pl: float | None = None,
                                usuario_id: str | None = None):
    iniciales = "".join([p[0] for p in usuario.split()[:2]]).upper() or "U"

    # Chip de saldo total de MT5 (equity). Si no hay dato, se muestra "—".
    if saldo is not None:
        saldo_txt = f"${saldo:,.2f} {moneda}"
    else:
        saldo_txt = "— sin conexión MT5"

    # P/G flotante (de posiciones abiertas) junto al saldo, estilo XM.
    # Siempre se dibuja el <span> (aunque esté vacío) para que el feed en vivo
    # (data-pj-acc, ver components/live_feed.py) pueda rellenarlo.
    pl_txt = f"{pl:+,.2f}" if pl is not None and abs(pl) >= 0.005 else ""
    color_pl = "#3fb950" if (pl or 0) >= 0 else "#f85149"
    pl_span = (
        f"<span data-pj-acc='profit' style='font-size:13px; font-weight:700; color:{color_pl}; "
        f"font-family:monospace;'>{pl_txt}</span>"
    )
    attr_saldo = "data-pj-acc='equity'" if saldo is not None else ""
    chip_saldo = (
        "<div style='display:flex; flex-direction:column; align-items:flex-end; "
        "line-height:1.1; padding:4px 12px; background:#161b22; border:1px solid #30363d; "
        "border-radius:8px;'>"
        "<span style='font-size:10px; color:#8b949e; text-transform:uppercase; "
        "letter-spacing:.5px;'>Saldo MT5</span>"
        "<span style='display:flex; align-items:baseline; gap:8px;'>"
        f"<span {attr_saldo} style='font-size:14px; font-weight:700; color:#3fb950; "
        f"font-family:monospace;'>{saldo_txt}</span>{pl_span}</span>"
        "</div>"
    )

    # Estilos de la navbar + del botón buscador
    st.markdown(
        """
        <style>
            .nav-user > summary { list-style: none; }
            .nav-user > summary::-webkit-details-marker { display: none; }
            .nav-user[open] .nav-flecha { transform: rotate(180deg); }
            .nav-menu-item:hover { background: #21262d; }
            .nav-ico { color:#8b949e; cursor:pointer; display:flex; align-items:center;
                       transition: color .15s ease; }
            .nav-ico:hover { color:#e6edf3; }
            /* Centrado vertical robusto */
            .st-key-barra_nav_fija [data-testid="stHorizontalBlock"] { align-items:center !important; }
            .st-key-barra_nav_fija [data-testid="stColumn"] {
                display:flex !important; flex-direction:column; justify-content:center !important;
            }
            .st-key-barra_nav_fija [data-testid="stColumn"] [data-testid="stMarkdownContainer"] { margin:0 !important; }
            .st-key-barra_nav_fija .stButton { margin:0 !important; }
            /* Grupo derecho (saldo · campana · usuario) pegado al borde: esas 3 columnas toman el ancho de su
               contenido y la columna vacía (3ª) absorbe todo el espacio sobrante. */
            .st-key-barra_nav_fija [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1) {
                flex:0 0 4% !important; min-width:0 !important; }
            .st-key-barra_nav_fija [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) {
                flex:0 0 26.5% !important; min-width:0 !important; }
            .st-key-barra_nav_fija [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3) {
                flex:1 1 0 !important; min-width:0 !important; }
            .st-key-barra_nav_fija [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(n+4) {
                flex:0 0 auto !important; width:auto !important; min-width:0 !important; }
            .st-key-barra_nav_fija [data-testid="stElementContainer"]:has(style) { display:none !important; }
            /* Botón que abre el buscador: se expande para aprovechar el espacio del antiguo logo */
            [class*="st-key-btn_abrir_buscador"] button {
                background:#161b22 !important; border:1px solid #30363d !important;
                border-radius:20px !important; color:#8b949e !important;
                justify-content:flex-start !important; font-weight:400 !important;
                padding:4px 16px !important; height:32px; min-height:32px !important;
            }
            [class*="st-key-btn_abrir_buscador"] button:hover {
                border-color:#58a6ff !important; color:#e6edf3 !important;
            }
            /* Campana de notificaciones (popover) con insignia */
            .st-key-notif_bell { position:relative; display:flex; justify-content:center; }
            .st-key-notif_bell [data-testid="stVerticalBlock"] { gap:0 !important; }
            .st-key-notif_bell [data-testid="stPopover"] button {
                background:transparent !important; border:none !important; box-shadow:none !important;
                color:#8b949e !important; padding:0 !important; min-height:32px !important; height:32px;
                width:32px !important; border-radius:8px !important; }
            .st-key-notif_bell [data-testid="stPopover"] button:hover { color:#e6edf3 !important;
                background:rgba(255,255,255,0.06) !important; }
            .st-key-notif_bell [data-testid="stPopoverButton"] div[aria-hidden="true"] { display:none !important; }
            .st-key-notif_bell [data-testid="stPopover"] button span[data-testid="stIconMaterial"] { font-size:22px !important; }
            .nt-badge { position:absolute; top:-3px; right:-1px; z-index:5; min-width:16px; height:16px; padding:0 4px;
                border-radius:999px; background:linear-gradient(135deg,#ff4b4b,#ff8f00); color:#fff; font-size:10px;
                font-weight:800; display:flex; align-items:center; justify-content:center; pointer-events:none;
                box-shadow:0 0 0 2px #0d1117; }
            [data-testid="stPopoverBody"] { min-width:350px; background:#0d1117 !important;
                border:1px solid #1f2937 !important; border-radius:14px !important; }
            .nt-cab { display:flex; justify-content:space-between; align-items:center; color:#fff; font-size:15px;
                font-weight:800; padding:2px 2px 6px; }
            .nt-cuenta { font-size:10.5px; font-weight:700; color:#ff8f00; background:rgba(255,143,0,.12);
                border:1px solid rgba(255,143,0,.35); border-radius:999px; padding:2px 9px; }
            .nt-item { display:flex; gap:10px; background:#151c27; border:1px solid #202a37; border-radius:12px;
                padding:9px 11px; margin-bottom:7px; }
            .nt-item.nueva { border-color:#3b2f22; background:#1a1f27; }
            .nt-ic { font-size:17px; line-height:1.2; }
            .nt-titulo { color:#e6edf3; font-size:13px; font-weight:700; display:flex; align-items:center; gap:7px; }
            .nt-punto { width:7px; height:7px; border-radius:50%; background:#ff8f00; }
            .nt-texto { color:#9aa5b1; font-size:12px; margin-top:2px; line-height:1.35; overflow-wrap:anywhere; }
            .nt-hace { color:#6b7686; font-size:10.5px; margin-top:3px; }
            .nt-vacio { color:#8b949e; font-size:12.5px; text-align:center; padding:18px 8px; line-height:1.45; }
            [data-testid="stPopoverBody"] [class*="st-key-notif_ir"] button { height:42px; border:none !important;
                border-radius:12px !important; background:linear-gradient(135deg,#ff4b4b 0%,#ff8f00 100%) !important;
                color:#fff !important; }
            [data-testid="stPopoverBody"] [class*="st-key-notif_leer"] button { height:42px; border-radius:12px !important;
                background:#161b22 !important; border:1px solid #30363d !important; color:#fff !important; }
            [data-testid="stPopoverBody"] [class*="st-key-notif_ir"] button p,
            [data-testid="stPopoverBody"] [class*="st-key-notif_leer"] button p { font-size:14px !important;
                font-weight:700 !important; color:#fff !important; }
            /* Botón ☰ que expande/colapsa la barra lateral (estilo SIGMA) */
            [class*="st-key-top_toggle"] button {
                background:transparent !important; border:none !important; box-shadow:none !important;
                color:#8b949e !important; padding:0 !important; height:40px; min-height:40px !important;
                width:40px !important; border-radius:8px !important;
            }
            [class*="st-key-top_toggle"] button:hover {
                color:#e6edf3 !important; background:rgba(255,255,255,0.06) !important;
            }
            [class*="st-key-top_toggle"] button p,
            [class*="st-key-top_toggle"] button p *,
            [class*="st-key-top_toggle"] button span[data-testid="stIconMaterial"] { font-size:28px !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    html_saldo = f"""
        <div style='display:flex; align-items:center; justify-content:flex-end; gap:18px; white-space:nowrap;'>
            {chip_saldo}
            <span class='nav-ico' title='Tema'>{_IC_TEMA}</span>
        </div>
    """

    html_usuario = f"""
        <div style='display:flex; align-items:center; justify-content:flex-end; white-space:nowrap;'>
            <details class='nav-user' style='position:relative;'>
                <summary style='display:flex; align-items:center; gap:8px; cursor:pointer;'>
                    <div style='width:30px; height:30px; border-radius:50%;
                                background:#1f6feb; color:#ffffff; display:flex;
                                align-items:center; justify-content:center;
                                font-weight:bold; font-size:12px;'>{iniciales}</div>
                    <span style='color:#e6edf3; font-size:13px;'>{usuario}</span>
                    <span class='nav-flecha' style='color:#8b949e; font-size:11px;
                          transition:transform .15s ease;'>▾</span>
                </summary>
                <div style='position:absolute; right:0; top:calc(100% + 10px);
                            background:#161b22; border:1px solid #30363d; border-radius:8px;
                            min-width:190px; padding:6px; z-index:3000;
                            box-shadow:0 8px 24px rgba(0,0,0,0.5);'>
                    <div class='nav-menu-item' style='display:flex; align-items:center; gap:10px;
                         padding:9px 12px; border-radius:6px; color:#e6edf3; font-size:13px;
                         cursor:pointer;'>👤 Mi perfil</div>
                    <div class='nav-menu-item' style='display:flex; align-items:center; gap:10px;
                         padding:9px 12px; border-radius:6px; color:#e6edf3; font-size:13px;
                         cursor:pointer;'>⚙️ Configuración</div>
                    <div style='height:1px; background:#30363d; margin:4px 6px;'></div>
                    <a href='?logout=1' target='_self' class='nav-menu-item'
                       style='display:flex; align-items:center; gap:10px;
                         padding:9px 12px; border-radius:6px; color:#f85149; font-size:13px;
                         cursor:pointer; text-decoration:none;'>🚪 Cerrar sesión</a>
                </div>
            </details>
        </div>
    """

    # ☰ + buscador (corto, a la izquierda) + espacio + saldo/tema + campana + usuario
    c_toggle, c_buscar, c_spacer, c_saldo, c_campana, c_usuario = st.columns(
        [0.2, 1.3, 1.49, 1.05, 0.16, 0.6], vertical_alignment="center")
    with c_toggle:
        # El clic lo intercepta un script en el navegador (nav_bar.py, _JS_SIDEBAR)
        # que alterna la barra lateral con animación CSS, SIN reejecutar Python.
        st.button(":material/menu:", key="top_toggle")
    with c_buscar:
        if st.button("Buscar activo, par o ticker...", icon=":material/search:",
                     key="btn_abrir_buscador", width="stretch"):
            abrir_buscador()
            st.rerun()
    with c_spacer:
        st.empty()
    with c_saldo:
        st.markdown(html_saldo, unsafe_allow_html=True)
    with c_campana:
        _campana(usuario_id or _usuario_id())
    with c_usuario:
        st.markdown(html_usuario, unsafe_allow_html=True)