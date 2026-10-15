"""Panel DERECHO: propuestas pendientes con Confirmar / Rechazar, interruptor de emergencia y vigilancias."""
from typing import Any

import streamlit as st

from componentes_plataforma.agente_paneles.datos import CLAVE_AVISO
from componentes_plataforma.agente_paneles.formato import cabecera_agente, clase_lado, esc, hora, kv, num, titulo, vacio
from componentes_plataforma.agente_paneles.vigilancias import seccion_vigilancias, usuario_id
from nucleo_agente import ordenes, vigilancia


def tarjeta_pendiente(o: dict[str, Any]) -> str:
    if o.get("accion") == "abrir":
        datos = (
            kv("Precio ref.", num(o.get("precio_ref")))
            + kv("Stop loss", num(o.get("sl")), "neg")
            + kv("Take profit", num(o.get("tp")), "pos")
        )
        extra = (
            f"<div class='ag-risk'>Riesgo ≈ <b>{(o.get('riesgo_dinero') or 0):.2f}</b> "
            f"· {(o.get('riesgo_pct') or 0):.2f}% del equity</div>"
        )
    else:
        datos = kv("Precio actual", num(o.get("precio_ref"))) + kv("Resultado", f"{(o.get('riesgo_dinero') or 0):+.2f}")
        extra = ""
    just = (o.get("justificacion") or "Sin justificación").strip()
    return (
        "<div class='ag-row'>"
        f"<div class='ag-top'><span class='ag-t'>Vence a las {hora(o.get('expira'))}</span>"
        "<span class='ag-badge' style='color:#f0b90b;border-color:#f0b90b55;background:#f0b90b18'>"
        "Pendiente</span></div>"
        f"<div class='ag-main'>{titulo(o)}</div>"
        f"<div class='ag-grid'>{datos}</div>{extra}"
        f"<div class='ag-quote'>{esc(just)}</div></div>"
    )


def alternar_bloqueo() -> None:
    ordenes.set_kill_switch(bool(st.session_state.get("kill_switch_ui")))


def renderizar_ordenes_propuestas(altura: int = 300) -> None:
    aviso = st.session_state.pop(CLAVE_AVISO, None)

    try:
        pendientes = ordenes.listar_pendientes()
        bloqueado = ordenes.kill_switch_activo()
        uid = usuario_id()
        vigs = vigilancia.listar(uid)
    except Exception as e:  # noqa: BLE001
        st.warning(f"No se pudieron leer las órdenes del agente: {e}")
        return

    with st.container(key="agp_panel"):
        st.html(cabecera_agente(
            "pending_actions", "Órdenes propuestas",
            "El agente propone y tú confirmas. Solo opera solo si autorizas una vigilancia. Solo cuenta demo.",
        ))
        if aviso:
            (st.success if aviso[0] == "ok" else st.error)(aviso[1])

        st.session_state["kill_switch_ui"] = bloqueado  # el interruptor refleja siempre lo guardado
        with st.container(key="agp_kill"):
            st.toggle(
                "⛔ Bloquear aperturas", key="kill_switch_ui", on_change=alternar_bloqueo,
                help="Interruptor de emergencia: no se podrán proponer ni confirmar aperturas.",
            )

        if not pendientes and not vigs:
            st.html(vacio(
                "inbox", "No hay órdenes pendientes ni vigilancias. Cuando el agente proponga una orden o "
                "una vigilancia, aparecerá aquí para que la autorices o la rechaces.",
            ))
            return

        contenedor = (
            st.container(height=altura, border=False, key="agp_scroll")
            if len(pendientes) + len(vigs) > 1 else st.container(border=False, key="agp_scroll")
        )
        with contenedor:
            if vigs:
                st.html("<div class='ag-sec'>Vigilancia automática</div>")
                if any(v["estado"] == vigilancia.ACTIVA for v in vigs):
                    # con vigilancias activas, solo esta sección se refresca sola (sin recargar la página)
                    st.fragment(run_every="8s")(seccion_vigilancias)(uid)
                else:
                    seccion_vigilancias(uid)
            if vigs and pendientes:
                st.html("<div class='ag-sec'>Órdenes pendientes</div>")
            for o in pendientes:
                with st.container(key=f"agp_card_{clase_lado(o)}_{o['id']}"):
                    st.html(tarjeta_pendiente(o))
                    if st.button("Confirmar orden", key=f"agp_ok_{o['id']}", icon=":material/check:",
                                 type="primary", width="stretch"):
                        res = ordenes.confirmar_orden(o["id"])
                        st.session_state[CLAVE_AVISO] = ("ok" if res["ok"] else "error", res["mensaje"])
                        st.rerun(scope="app")  # refresca también el historial de la izquierda
                    if st.button("Rechazar", key=f"agp_no_{o['id']}", width="stretch"):
                        ordenes.rechazar_orden(o["id"])
                        st.rerun(scope="app")
