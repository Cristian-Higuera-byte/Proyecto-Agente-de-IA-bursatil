"""Paneles del agente en los costados del dashboard (Fase 1).

NOMBRE DEL ARCHIVO: components/panel_ordenes.py

  * renderizar_historial_agente()   -> panel IZQUIERDO (bajo la watchlist): historial
    permanente de cada orden que el agente propuso, ejecutada, rechazada o bloqueada.
  * renderizar_ordenes_propuestas() -> panel DERECHO (sobre el ticket): propuestas
    pendientes con Confirmar / Rechazar, interruptor de emergencia y avisos.

Se llaman desde watchlist.py y order_panel.py, así que se dibujan en CADA ejecución de la
app, hagas o no una petición al agente (ya no dependen del chat).

No usan run_every: un temporizador reinicia la ejecución en curso y cortaría la respuesta
del agente mientras escribe. En su lugar, central_panel.py hace un st.rerun() al terminar un
turno en el que el agente propuso algo, y Confirmar / Rechazar refrescan toda la app.

Solo este módulo (vía core.ordenes.confirmar_orden) puede hacer que una orden llegue a MT5.
"""

from __future__ import annotations

import html
import traceback
from datetime import datetime
from typing import Any

import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx

from core import ordenes

_CLAVE_AVISO = "_aviso_orden"


def _ya_dibujado(clave: str, funcion: str) -> bool:
    """True si ya se dibujó un contenedor con esa clave en ESTA ejecución.

    Evita StreamlitDuplicateElementKey cuando una función se llama dos veces (p. ej. quedó
    una llamada vieja en otro archivo). En ese caso la segunda llamada se omite y, una sola
    vez por sesión, se imprime en la terminal desde dónde se llamó, para poder borrarla.
    """
    ctx = get_script_run_ctx()
    if ctx is None or clave not in getattr(ctx, "widget_user_keys_this_run", ()):
        return False
    marca = f"_dup_avisado_{clave}"
    if not st.session_state.get(marca):
        st.session_state[marca] = True
        pila = "".join(traceback.format_stack(limit=6)[:-1])
        print(f"\n[panel_ordenes] {funcion}() se llamó DOS veces en la misma ejecución; "
              f"se omite la segunda.\nSegunda llamada desde:\n{pila}")
    return True

_CSS = """
<style>
  .st-key-agh_panel, .st-key-agp_panel { background:#0d1117; border:1px solid #1f2937;
      border-radius:14px; padding:14px 14px 12px; }
  .st-key-agh_panel [data-testid="stVerticalBlock"],
  .st-key-agp_panel [data-testid="stVerticalBlock"] { gap:8px; }
  .st-key-agh_scroll, .st-key-agp_scroll { scrollbar-width:thin; scrollbar-color:#2b3550 transparent; }
  .ag-h { color:#e6edf3; font-weight:800; font-size:15px; margin:0 0 2px; }
  .ag-sub { color:#8b949e; font-size:11.5px; margin:0; line-height:1.35; }
  .ag-row { background:#0f1620; border:1px solid #202a37; border-radius:10px;
      padding:8px 10px; margin-bottom:8px; }
  .ag-top { display:flex; justify-content:space-between; align-items:center; gap:8px; }
  .ag-t { color:#8b949e; font-size:11px; }
  .ag-badge { font-size:10.5px; font-weight:700; padding:2px 8px; border-radius:999px;
      border:1px solid; white-space:nowrap; }
  .ag-main { color:#e6edf3; font-size:13px; font-weight:700; margin-top:4px; }
  .ag-main .buy { color:#2ebd85; } .ag-main .sell { color:#f6465d; }
  .ag-det { color:#8b949e; font-size:11.5px; margin-top:3px; line-height:1.35; overflow-wrap:anywhere; }
  .ag-empty { color:#8b949e; font-size:12.5px; padding:4px 2px; line-height:1.4; }
</style>
"""

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


def _fila_historial(o: dict[str, Any]) -> str:
    estado = str(o.get("estado") or "")
    etiqueta, color = _ESTADOS.get(estado, (estado or "Desconocido", "#8b949e"))
    return (
        "<div class='ag-row'>"
        f"<div class='ag-top'><span class='ag-t'>{_hora(o.get('creada'))}</span>"
        f"<span class='ag-badge' style='color:{color};border-color:{color}55;background:{color}18'>"
        f"{_e(etiqueta)}</span></div>"
        f"<div class='ag-main'>{_titulo(o)}</div>{_detalle(o)}</div>"
    )


def _tarjeta_pendiente(o: dict[str, Any]) -> str:
    if o.get("accion") == "abrir":
        linea = (
            f"Precio ref. {_num(o.get('precio_ref'))} · SL {_num(o.get('sl'))} · TP {_num(o.get('tp'))}<br>"
            f"Riesgo ≈ {(o.get('riesgo_dinero') or 0):.2f} ({(o.get('riesgo_pct') or 0):.2f}% del equity)"
        )
    else:
        linea = f"Resultado actual ≈ {(o.get('riesgo_dinero') or 0):.2f}"
    just = (o.get("justificacion") or "Sin justificación").strip()
    return (
        "<div class='ag-row' style='margin-bottom:0'>"
        f"<div class='ag-top'><span class='ag-t'>Vence a las {_hora(o.get('expira'))}</span>"
        "<span class='ag-badge' style='color:#f0b90b;border-color:#f0b90b55;background:#f0b90b18'>"
        "Pendiente</span></div>"
        f"<div class='ag-main'>{_titulo(o)}</div>"
        f"<div class='ag-det'>{linea}</div>"
        f"<div class='ag-det'>💬 {_e(just)}</div></div>"
    )


# ── Panel IZQUIERDO: historial permanente ─────────────────────────────────────────────
def renderizar_historial_agente(limite: int = 30, altura: int = 300) -> None:
    if _ya_dibujado("agh_panel", "renderizar_historial_agente"):
        return
    st.html(_CSS)
    try:
        ordenes.listar_pendientes()  # marca como vencidas las propuestas que ya expiraron
        historial = ordenes.listar_historial(limite)
    except Exception as e:  # noqa: BLE001
        st.warning(f"No se pudo leer el historial del agente: {e}")
        return

    with st.container(key="agh_panel"):
        st.html(
            "<div class='ag-h'>🤖 Historial del agente</div>"
            "<div class='ag-sub'>Cada orden que propone, ejecuta o se bloquea.</div>"
        )
        with st.container(height=altura, border=False, key="agh_scroll"):
            if not historial:
                st.html("<div class='ag-empty'>Aún no hay órdenes registradas.</div>")
            else:
                st.html("".join(_fila_historial(o) for o in historial))


# ── Panel DERECHO: propuestas pendientes ──────────────────────────────────────────────
def _alternar_bloqueo() -> None:
    ordenes.set_kill_switch(bool(st.session_state.get("kill_switch_ui")))


def renderizar_ordenes_propuestas(altura: int = 300) -> None:
    if _ya_dibujado("agp_panel", "renderizar_ordenes_propuestas"):
        return
    st.html(_CSS)
    aviso = st.session_state.pop(_CLAVE_AVISO, None)

    try:
        pendientes = ordenes.listar_pendientes()
        bloqueado = ordenes.kill_switch_activo()
    except Exception as e:  # noqa: BLE001
        st.warning(f"No se pudieron leer las órdenes del agente: {e}")
        return

    with st.container(key="agp_panel"):
        st.html(
            "<div class='ag-h'>📋 Órdenes propuestas por el agente</div>"
            "<div class='ag-sub'>El agente propone y tú confirmas. Solo cuenta demo: "
            "nada se ejecuta sin tu botón.</div>"
        )
        if aviso:
            (st.success if aviso[0] == "ok" else st.error)(aviso[1])

        st.session_state["kill_switch_ui"] = bloqueado  # el interruptor refleja siempre lo guardado
        st.toggle(
            "⛔ Bloquear nuevas aperturas", key="kill_switch_ui", on_change=_alternar_bloqueo,
            help="Interruptor de emergencia: no se podrán proponer ni confirmar aperturas.",
        )

        if not pendientes:
            st.html(
                "<div class='ag-empty'>No hay órdenes pendientes. Cuando el agente proponga una, "
                "aparecerá aquí para que la confirmes o la rechaces.</div>"
            )
            return

        contenedor = (
            st.container(height=altura, border=False, key="agp_scroll")
            if len(pendientes) > 1 else st.container(border=False, key="agp_scroll")
        )
        with contenedor:
            for o in pendientes:
                with st.container(key=f"agp_card_{o['id']}"):
                    st.html(_tarjeta_pendiente(o))
                    c_ok, c_no = st.columns(2)
                    if c_ok.button("Confirmar", key=f"agp_ok_{o['id']}", icon=":material/check:",
                                   type="primary", width="stretch"):
                        res = ordenes.confirmar_orden(o["id"])
                        st.session_state[_CLAVE_AVISO] = ("ok" if res["ok"] else "error", res["mensaje"])
                        st.rerun(scope="app")  # refresca también el historial de la izquierda
                    if c_no.button("Rechazar", key=f"agp_no_{o['id']}", width="stretch"):
                        ordenes.rechazar_orden(o["id"])
                        st.rerun(scope="app")