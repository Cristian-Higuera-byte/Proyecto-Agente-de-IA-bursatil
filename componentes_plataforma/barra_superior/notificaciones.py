"""Campana de notificaciones: insignia, lista desplegable (popover), avisos emergentes y vigilancia de avisos nuevos."""
import html
import time

import streamlit as st

from componentes_plataforma.barra_superior.datos import ICONO_TIPO
from nucleo_agente import notificaciones


def usuario_id() -> str:
    return str((st.session_state.get("usuario_info") or {}).get("id") or "local")


def hace(creada: float) -> str:
    seg = max(0, int(time.time() - creada))
    if seg < 60:
        return "ahora"
    if seg < 3600:
        return f"hace {seg // 60} min"
    if seg < 86400:
        return f"hace {seg // 3600} h"
    return f"hace {seg // 86400} d"


def html_notificaciones(items: list) -> str:
    if not items:
        return ("<div class='nt-vacio'>Sin notificaciones por ahora. Aquí te avisamos cuando el agente "
                "termine de responder.</div>")
    filas = []
    for n in items:
        punto = "" if n["leida"] else "<span class='nt-punto'></span>"
        filas.append(
            f"<div class='nt-item{'' if n['leida'] else ' nueva'}'>"
            f"<div class='nt-ic'>{ICONO_TIPO.get(n['tipo'], '🔔')}</div>"
            f"<div class='nt-cuerpo'><div class='nt-titulo'>{html.escape(n['titulo'])}{punto}</div>"
            f"<div class='nt-texto'>{html.escape(n['texto'])}</div>"
            f"<div class='nt-hace'>{hace(n['creada'])}</div></div></div>"
        )
    return "".join(filas)


@st.fragment(run_every="3s")
def vigilar_notificaciones(usuario_id: str) -> None:
    """Revisa cada 3 s (sin dibujar nada) si llegó un aviso nuevo. Solo entonces refresca la app,
    para que aparezcan la insignia y el toast aunque el usuario esté en otra sección."""
    if notificaciones.ultima_id(usuario_id) != st.session_state.get("_notif_ultima_id"):
        st.rerun(scope="app")


def campana(usuario_id: str) -> None:
    """Campana con insignia + lista desplegable (popover de Streamlit: sus botones son reales)."""
    st.session_state["_notif_ultima_id"] = notificaciones.ultima_id(usuario_id)
    items = notificaciones.listar(usuario_id, 8)
    sin_leer = notificaciones.no_leidas(usuario_id)

    # Aviso emergente, una sola vez por notificación y sesión.
    vistas = st.session_state.setdefault("_notif_toast", set())
    for n in reversed(items):
        if not n["leida"] and n["id"] not in vistas:
            vistas.add(n["id"])
            st.toast(f"**{n['titulo']}**\n\n{n['texto']}", icon=ICONO_TIPO.get(n["tipo"], "🔔"))

    with st.container(key="notif_bell"):
        if sin_leer:
            st.html(f"<span class='nt-badge'>{sin_leer if sin_leer < 10 else '9+'}</span>")
        with st.popover("", icon=":material/notifications:"):
            st.html(
                "<div class='nt-cab'>Notificaciones"
                + (f"<span class='nt-cuenta'>{sin_leer} nueva{'s' if sin_leer != 1 else ''}</span>" if sin_leer else "")
                + "</div>"
            )
            st.html(html_notificaciones(items))
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
    vigilar_notificaciones(usuario_id)
