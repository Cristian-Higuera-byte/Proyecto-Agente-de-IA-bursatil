"""Paneles del agente en los costados del dashboard (Fase 1).

NOMBRE DEL ARCHIVO: components/panel_ordenes.py

  * renderizar_historial_agente()   -> panel IZQUIERDO (bajo la watchlist): historial
    permanente de cada orden que el agente propuso, ejecutada, rechazada o bloqueada.
  * renderizar_ordenes_propuestas() -> panel DERECHO (sobre el ticket): propuestas
    pendientes con Confirmar / Rechazar, interruptor de emergencia y avisos.

Se llaman desde app.py (vistas Trading y Cartera), así que se dibujan en CADA ejecución de la
app, hagas o no una petición al agente (ya no dependen del chat). app.py llama una sola vez a
inyectar_estilos_agente() para cargar el CSS de ambos paneles.

No usan run_every: un temporizador reinicia la ejecución en curso y cortaría la respuesta
del agente mientras escribe. En su lugar, central_panel.py hace un st.rerun() al terminar un
turno en el que el agente propuso algo, y Confirmar / Rechazar refrescan toda la app.

Solo este módulo (vía core.ordenes.confirmar_orden) puede hacer que una orden llegue a MT5.
"""

from __future__ import annotations

import html
from datetime import datetime
from typing import Any

import streamlit as st

from core import ordenes

_CLAVE_AVISO = "_aviso_orden"


_CSS = """
<style>
  /* ═══ Sección del agente (historial · chat · propuestas) ═══
     Misma línea visual que "Lista de activos" y "Cartera": paneles #0d1117, filas #151c27,
     cabecera con icono en degradado naranja y botones naranja / oscuro como el modal de cierre. */
  .st-key-agh_panel, .st-key-agp_panel, .st-key-agc_panel { background:#0d1117; border:1px solid #1f2937;
      border-radius:14px; padding:0 0 14px; overflow:hidden; }
  .st-key-agh_panel [data-testid="stVerticalBlock"], .st-key-agp_panel [data-testid="stVerticalBlock"],
  .st-key-agc_panel [data-testid="stVerticalBlock"] { gap:10px; }
  .st-key-agh_panel div[data-testid="stVerticalBlockBorderWrapper"],
  .st-key-agp_panel div[data-testid="stVerticalBlockBorderWrapper"],
  .st-key-agc_panel div[data-testid="stVerticalBlockBorderWrapper"] { background:transparent !important; border:none !important; }

  /* Zonas con scroll: dentro del panel, con márgenes laterales */
  .st-key-agh_scroll, .st-key-agp_scroll, .st-key-agc_scroll { margin:0 14px; width:calc(100% - 28px) !important;
      scrollbar-width:thin; scrollbar-color:#2b3550 transparent; }

  /* Cabecera (igual que .wl-head / .ca-head) */
  .ag-head { display:flex; align-items:center; gap:11px; padding:16px 16px 2px; }
  .ag-head .ic { width:38px; height:38px; border-radius:11px; flex:0 0 auto; display:flex; align-items:center;
      justify-content:center; background:linear-gradient(135deg,rgba(255,75,75,.16),rgba(255,143,0,.16));
      border:1px solid #2a2320; }
  .ag-mi { font-family:'Material Symbols Rounded'; font-weight:400; font-size:21px; line-height:1;
      background:linear-gradient(135deg,#ff6a3d,#ff8f00); -webkit-background-clip:text; background-clip:text;
      color:transparent; }
  .ag-title { color:#fff; font-size:16px; font-weight:800; letter-spacing:.2px; line-height:1.1; }
  .ag-sub { color:#8b949e; font-size:11.5px; margin-top:2px; line-height:1.35; }

  /* Filas del historial y tarjetas pendientes */
  .ag-row { position:relative; background:#151c27; border:1px solid #202a37; border-radius:12px;
      padding:10px 12px 10px 16px; margin-bottom:8px; box-sizing:border-box; }
  .ag-row::before { content:""; position:absolute; left:0; top:0; bottom:0; width:3px;
      border-radius:3px 0 0 3px; background:#3a4658; }
  .ag-top { display:flex; justify-content:space-between; align-items:center; gap:8px; }
  .ag-t { color:#8b949e; font-size:11px; }
  .ag-badge { font-size:10px; font-weight:800; letter-spacing:.5px; padding:2px 9px; border-radius:999px;
      border:1px solid; white-space:nowrap; }
  .ag-main { color:#fff; font-size:13.5px; font-weight:800; margin-top:5px; letter-spacing:.2px; }
  .ag-main .buy { color:#2ebd85; } .ag-main .sell { color:#f6465d; }
  .ag-det { color:#8b949e; font-size:11.5px; margin-top:4px; line-height:1.4; overflow-wrap:anywhere; }

  /* Datos de la propuesta en cuadritos (números en monoespaciada, como el ticket de orden) */
  .ag-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(64px,1fr)); gap:6px; margin-top:9px; }
  .ag-kv { background:#0f1620; border:1px solid #202a37; border-radius:9px; padding:5px 7px; min-width:0; }
  .ag-kv span { display:block; color:#8b949e; font-size:9.5px; letter-spacing:.2px; white-space:nowrap; }
  .ag-kv b { display:block; color:#e6edf3; font-size:12px; font-weight:700; margin-top:1px; white-space:nowrap;
      font-family:ui-monospace,Consolas,monospace; overflow:hidden; text-overflow:ellipsis; }
  .ag-kv b.neg { color:#f6465d; } .ag-kv b.pos { color:#2ebd85; }
  .ag-risk { color:#c9d1d9; font-size:12px; margin-top:8px; }
  .ag-risk b { color:#ff8f00; font-family:ui-monospace,Consolas,monospace; }
  .ag-quote { color:#9aa5b1; font-size:11.5px; line-height:1.4; margin-top:8px; padding-left:9px;
      border-left:2px solid #2b3546; overflow-wrap:anywhere; }

  /* Estado vacío (mismo recuadro punteado que "posición cerrada" de Cartera) */
  .ag-empty { margin:0 14px; padding:20px 14px; text-align:center; background:#12161d;
      border:1px dashed #33425c; border-radius:12px; color:#8b949e; font-size:12.5px; line-height:1.45; }
  .ag-empty .ag-mi { display:block; font-size:26px; margin-bottom:6px; }

  /* Propuestas: tarjeta con botones, interruptor y avisos */
  .st-key-agp_panel [class*="st-key-agp_card_"] { position:relative; background:#151c27; border:1px solid #202a37;
      border-radius:12px; padding:12px 12px 12px 16px; overflow:hidden; }
  .st-key-agp_panel [class*="st-key-agp_card_"]::before { content:""; position:absolute; left:0; top:0; bottom:0;
      width:3px; background:#3a4658; }
  .st-key-agp_panel [class*="st-key-agp_card_"] [data-testid="stVerticalBlock"] { gap:8px; }
  .ag-row.buy::before, .st-key-agp_panel [class*="st-key-agp_card_buy_"]::before {
      background:linear-gradient(180deg,#3fb950,#2ea043); }
  .ag-row.sell::before, .st-key-agp_panel [class*="st-key-agp_card_sell_"]::before {
      background:linear-gradient(180deg,#f85149,#da3633); }
  .st-key-agp_panel [class*="st-key-agp_card_"] .ag-row { background:transparent; border:none; padding:0;
      margin:0; }
  .st-key-agp_panel [class*="st-key-agp_card_"] .ag-row::before { display:none; }
  .st-key-agp_kill { margin:0 14px; width:calc(100% - 28px) !important; background:#0f1620; border:1px solid #202a37;
      border-radius:12px; padding:9px 13px; }
  .st-key-agp_panel [data-testid="stAlert"] { margin:0 14px; border-radius:12px; }

  /* Botones: principal = degradado naranja P&J, secundario = oscuro (igual que el modal "Cerrar posición") */
  .st-key-agp_panel [class*="st-key-agp_ok_"] button { height:44px; border:none !important; border-radius:12px !important;
      background:linear-gradient(135deg,#ff4b4b 0%,#ff8f00 100%) !important; color:#fff !important; }
  .st-key-agp_panel [class*="st-key-agp_ok_"] button:hover { filter:brightness(1.1); }
  .st-key-agp_panel [class*="st-key-agp_no_"] button, .st-key-agc_panel .st-key-agc_nueva button {
      height:44px; border-radius:12px !important; background:#161b22 !important; border:1px solid #30363d !important;
      color:#fff !important; }
  .st-key-agp_panel [class*="st-key-agp_no_"] button:hover, .st-key-agc_panel .st-key-agc_nueva button:hover {
      border-color:#58a6ff !important; background:#21262d !important; }
  .st-key-agp_panel [class*="st-key-agp_ok_"] button p, .st-key-agp_panel [class*="st-key-agp_no_"] button p,
  .st-key-agc_panel .st-key-agc_nueva button p { font-size:14px !important; font-weight:700 !important;
      color:#fff !important; }

  /* Respuesta en curso: punto que late + fase actual + cronómetro */
  .ag-live { display:flex; align-items:center; gap:9px; margin:0 0 8px; }
  .ag-dot { width:8px; height:8px; border-radius:50%; background:#ff8f00; flex:0 0 auto;
      animation:ag-pulso 1.4s infinite; }
  @keyframes ag-pulso { 0% { box-shadow:0 0 0 0 rgba(255,143,0,.55); } 70% { box-shadow:0 0 0 8px rgba(255,143,0,0); }
      100% { box-shadow:0 0 0 0 rgba(255,143,0,0); } }
  .ag-fase { color:#c9d1d9; font-size:12.5px; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .ag-reloj { margin-left:auto; flex:0 0 auto; font-family:ui-monospace,Consolas,monospace; font-size:12px;
      font-weight:700; color:#ff8f00; background:rgba(255,143,0,.1); border:1px solid rgba(255,143,0,.3);
      border-radius:999px; padding:2px 10px; }

  /* Botón Detener (consulta en curso): compacto, oscuro y rojo al pasar el cursor */
  .st-key-agc_panel [class*="st-key-agc_stop_"] button { height:34px; min-height:34px; padding:0 14px;
      border-radius:10px !important; background:#161b22 !important; border:1px solid #30363d !important;
      color:#e6edf3 !important; }
  .st-key-agc_panel [class*="st-key-agc_stop_"] button:hover:not(:disabled) { border-color:#f85149 !important;
      color:#f85149 !important; background:#21262d !important; }
  .st-key-agc_panel [class*="st-key-agc_stop_"] button:disabled { opacity:.65; }
  .st-key-agc_panel [class*="st-key-agc_stop_"] button p { font-size:13px !important; font-weight:700 !important; }

  /* Chat */
  .st-key-agc_panel [data-testid="stHorizontalBlock"] { padding:0 14px; gap:10px; align-items:center; }
  .st-key-agc_panel div[data-baseweb="select"] > div { min-height:44px; border-radius:12px !important;
      background:#161b22 !important; border:1px solid #30363d !important; }
  .st-key-agc_scroll { background:#0b0f19; border:1px solid #1f2937 !important; border-radius:12px; padding:10px; }
  .st-key-agc_panel [data-testid="stChatMessage"] { background:#151c27; border:1px solid #202a37; border-radius:12px;
      padding:12px 14px; margin-bottom:8px; }
  .st-key-agc_panel [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
      background:#19212e; border-color:#36465f; }
  .st-key-agc_panel [data-testid="stChatMessageAvatarUser"] { background:#1f6feb !important; color:#fff !important; }
  .st-key-agc_panel [data-testid="stChatMessage"] p { font-size:14px; line-height:1.5; }
  .st-key-agc_panel [data-testid="stChatMessage"] [data-testid="stCaptionContainer"] { color:#6b7686; }
  .st-key-agc_panel [data-testid="stChatInput"] { margin:0 14px; width:calc(100% - 28px); background:#0f1620 !important;
      border:1px solid #2b3546 !important; border-radius:12px !important; box-shadow:none !important; }
  .st-key-agc_panel [data-testid="stChatInput"]:focus-within { border-color:#ff8f00 !important; }
  .st-key-agc_panel [data-testid="stChatInput"] > div, .st-key-agc_panel [data-testid="stChatInput"] textarea {
      background:transparent !important; color:#e6edf3 !important; }
  .st-key-agc_panel [data-testid="stChatInputSubmitButton"] { background:linear-gradient(135deg,#ff4b4b,#ff8f00) !important;
      color:#fff !important; border-radius:9px !important; }
</style>
"""


def inyectar_estilos_agente() -> None:
    """Carga el CSS de los dos paneles del agente. Llamar UNA vez por ejecución (lo hace app.py)."""
    st.html(_CSS)


# estado -> (texto, color)
_ESTADOS = {
    "PENDIENTE": ("Pendiente", "#f0b90b"),
    "EJECUTANDO": ("Ejecutando…", "#f0b90b"),
    "EJECUTADA": ("Ejecutada", "#2ebd85"),
    "RECHAZADA_USUARIO": ("Rechazada por ti", "#8b949e"),
    "RECHAZADA_RIESGO": ("Bloqueada por riesgo", "#f6465d"),
    "EXPIRADA": ("Vencida", "#8b949e"),
    "ERROR": ("Error", "#f6465d"),
}


# ── Utilidades de formato (todo texto que viene del agente/MT5 se escapa) ─────────────
def _e(valor: Any) -> str:
    return html.escape("" if valor is None else str(valor), quote=True)


def _num(valor: Any) -> str:
    if valor in (None, 0, ""):
        return "—"
    try:
        return f"{float(valor):.5f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return _e(valor)


def _hora(iso: Any) -> str:
    try:
        dt = datetime.fromisoformat(str(iso))
    except (TypeError, ValueError):
        return _e(iso)
    return dt.strftime("%H:%M") if dt.date() == datetime.now().date() else dt.strftime("%d/%m %H:%M")


def _titulo(o: dict[str, Any]) -> str:
    simbolo = _e(o.get("simbolo") or "—")
    if o.get("accion") == "cerrar":
        ticket = f"#{_e(o['ticket_objetivo'])}" if o.get("ticket_objetivo") else "posición"
        return f"CERRAR {ticket} · {simbolo}"
    lado = str(o.get("lado") or "").lower()
    clase = "buy" if lado == "compra" else "sell" if lado == "venta" else ""
    try:
        vol = f" {float(o['volumen']):g}" if o.get("volumen") else ""
    except (TypeError, ValueError):
        vol = ""
    return f"<span class='{clase}'>{_e(lado.upper() or '—')}</span>{vol} · {simbolo}"


def _detalle(o: dict[str, Any]) -> str:
    if o.get("estado") in ("EJECUTADA", "RECHAZADA_RIESGO", "ERROR"):
        txt = o.get("detalle") or o.get("justificacion")
    else:
        txt = o.get("justificacion") or o.get("detalle")
    txt = (txt or "").strip()
    corto = txt if len(txt) <= 110 else txt[:107] + "…"
    return f"<div class='ag-det' title='{_e(txt)}'>{_e(corto)}</div>" if txt else ""


def _clase_lado(o: dict[str, Any]) -> str:
    """'buy' | 'sell' | 'cerrar': define el color de la franja lateral de la fila."""
    if o.get("accion") == "cerrar":
        return "cerrar"
    lado = str(o.get("lado") or "").lower()
    return "buy" if lado == "compra" else "sell" if lado == "venta" else "cerrar"


def cabecera_agente(icono: str, titulo: str, subtitulo: str) -> str:
    """Cabecera de panel (icono Material + título + subtítulo), igual que 'Lista de activos'."""
    return (
        f"<div class='ag-head'><div class='ic'><span class='ag-mi'>{_e(icono)}</span></div>"
        f"<div><div class='ag-title'>{_e(titulo)}</div><div class='ag-sub'>{_e(subtitulo)}</div></div></div>"
    )


def _vacio(icono: str, texto: str) -> str:
    return f"<div class='ag-empty'><span class='ag-mi'>{_e(icono)}</span>{_e(texto)}</div>"


def _fila_historial(o: dict[str, Any]) -> str:
    estado = str(o.get("estado") or "")
    etiqueta, color = _ESTADOS.get(estado, (estado or "Desconocido", "#8b949e"))
    return (
        f"<div class='ag-row {_clase_lado(o)}'>"
        f"<div class='ag-top'><span class='ag-t'>{_hora(o.get('creada'))}</span>"
        f"<span class='ag-badge' style='color:{color};border-color:{color}55;background:{color}18'>"
        f"{_e(etiqueta)}</span></div>"
        f"<div class='ag-main'>{_titulo(o)}</div>{_detalle(o)}</div>"
    )


def _kv(etiqueta: str, valor: str, clase: str = "") -> str:
    return f"<div class='ag-kv'><span>{_e(etiqueta)}</span><b class='{clase}'>{valor}</b></div>"


def _tarjeta_pendiente(o: dict[str, Any]) -> str:
    if o.get("accion") == "abrir":
        datos = (
            _kv("Precio ref.", _num(o.get("precio_ref")))
            + _kv("Stop loss", _num(o.get("sl")), "neg")
            + _kv("Take profit", _num(o.get("tp")), "pos")
        )
        extra = (
            f"<div class='ag-risk'>Riesgo ≈ <b>{(o.get('riesgo_dinero') or 0):.2f}</b> "
            f"· {(o.get('riesgo_pct') or 0):.2f}% del equity</div>"
        )
    else:
        datos = _kv("Precio actual", _num(o.get("precio_ref"))) + _kv("Resultado", f"{(o.get('riesgo_dinero') or 0):+.2f}")
        extra = ""
    just = (o.get("justificacion") or "Sin justificación").strip()
    return (
        "<div class='ag-row'>"
        f"<div class='ag-top'><span class='ag-t'>Vence a las {_hora(o.get('expira'))}</span>"
        "<span class='ag-badge' style='color:#f0b90b;border-color:#f0b90b55;background:#f0b90b18'>"
        "Pendiente</span></div>"
        f"<div class='ag-main'>{_titulo(o)}</div>"
        f"<div class='ag-grid'>{datos}</div>{extra}"
        f"<div class='ag-quote'>{_e(just)}</div></div>"
    )


# ── Panel IZQUIERDO: historial permanente ─────────────────────────────────────────────
def renderizar_historial_agente(limite: int = 30, altura: int = 300) -> None:
    try:
        ordenes.expirar_vencidas()  # marca como vencidas las propuestas que ya expiraron
        historial = ordenes.listar_historial(limite)
    except Exception as e:  # noqa: BLE001
        st.warning(f"No se pudo leer el historial del agente: {e}")
        return

    with st.container(key="agh_panel"):
        st.html(cabecera_agente("history", "Historial del agente", "Cada orden que propone, ejecuta o se bloquea."))
        with st.container(height=altura, border=False, key="agh_scroll"):
            if not historial:
                st.html(_vacio("history", "Aún no hay órdenes registradas."))
            else:
                st.html("".join(_fila_historial(o) for o in historial))


# ── Panel DERECHO: propuestas pendientes ──────────────────────────────────────────────
def _alternar_bloqueo() -> None:
    ordenes.set_kill_switch(bool(st.session_state.get("kill_switch_ui")))


def renderizar_ordenes_propuestas(altura: int = 300) -> None:
    aviso = st.session_state.pop(_CLAVE_AVISO, None)

    try:
        pendientes = ordenes.listar_pendientes()
        bloqueado = ordenes.kill_switch_activo()
    except Exception as e:  # noqa: BLE001
        st.warning(f"No se pudieron leer las órdenes del agente: {e}")
        return

    with st.container(key="agp_panel"):
        st.html(cabecera_agente(
            "pending_actions", "Órdenes propuestas",
            "El agente propone y tú confirmas. Solo cuenta demo: nada se ejecuta sin tu botón.",
        ))
        if aviso:
            (st.success if aviso[0] == "ok" else st.error)(aviso[1])

        st.session_state["kill_switch_ui"] = bloqueado  # el interruptor refleja siempre lo guardado
        with st.container(key="agp_kill"):
            st.toggle(
                "⛔ Bloquear aperturas", key="kill_switch_ui", on_change=_alternar_bloqueo,
                help="Interruptor de emergencia: no se podrán proponer ni confirmar aperturas.",
            )

        if not pendientes:
            st.html(_vacio(
                "inbox", "No hay órdenes pendientes. Cuando el agente proponga una, "
                "aparecerá aquí para que la confirmes o la rechaces.",
            ))
            return

        contenedor = (
            st.container(height=altura, border=False, key="agp_scroll")
            if len(pendientes) > 1 else st.container(border=False, key="agp_scroll")
        )
        with contenedor:
            for o in pendientes:
                with st.container(key=f"agp_card_{_clase_lado(o)}_{o['id']}"):
                    st.html(_tarjeta_pendiente(o))
                    if st.button("Confirmar orden", key=f"agp_ok_{o['id']}", icon=":material/check:",
                                 type="primary", width="stretch"):
                        res = ordenes.confirmar_orden(o["id"])
                        st.session_state[_CLAVE_AVISO] = ("ok" if res["ok"] else "error", res["mensaje"])
                        st.rerun(scope="app")  # refresca también el historial de la izquierda
                    if st.button("Rechazar", key=f"agp_no_{o['id']}", width="stretch"):
                        ordenes.rechazar_orden(o["id"])
                        st.rerun(scope="app")