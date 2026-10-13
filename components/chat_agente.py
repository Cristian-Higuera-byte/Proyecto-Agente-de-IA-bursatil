"""Chat del agente de IA (core.agente.Agente): conversación, turno en segundo plano y botón de detener.

Va en la fila de abajo de app.py, junto al historial y las órdenes propuestas.
"""
from __future__ import annotations

import os
import time
from html import escape

import streamlit as st

import config
from components.panel_ordenes import cabecera_agente
from core import turnos
from core.agente import Agente  # type: ignore[import-untyped]


_SALUDO = (
    "¡Hola! Estoy listo. Pregúntame sobre cualquier activo, mercado o "
    "pídeme gráficos y su respectiva imagen renderizada."
)


def _usuario_id() -> str:
    """Id del usuario con sesión iniciada: clave del turno en segundo plano y de las notificaciones."""
    return str((st.session_state.get("usuario_info") or {}).get("id") or "local")


def _obtener_agente():
    """Devuelve (agente, mensaje_error). Un agente por usuario: sobrevive a recargas de la página,
    así un turno en curso y la conversación no se pierden."""
    agente = st.session_state.get("agente_ia")
    if agente is not None:
        return agente, ""
    uid = _usuario_id()
    agente = turnos.agente_de(uid)
    if agente is None:
        try:
            agente = Agente(usuario_id="local")  # cambiar si el dashboard tiene login
        except Exception as e:
            return None, f"No se pudo iniciar el agente: {e}"
        turnos.registrar_agente(uid, agente)
    st.session_state["agente_ia"] = agente
    return agente, ""


def _cambiar_perfil():
    agente = st.session_state.get("agente_ia")
    if agente is not None:
        agente.perfil = st.session_state["perfil_agente"]


def renderizar_chat_agente() -> None:
    """Chat del agente. Va en la fila de abajo de app.py, junto al historial y las propuestas."""
    with st.container(key="agc_panel"):   # tarjeta con el mismo estilo que el historial y las propuestas
        st.html(cabecera_agente(
            "smart_toy", "Agente IA Analítico",
            "Consola, gráficos e imágenes · mantiene el contexto y usa las herramientas de MT5",
        ))
        _chat_agente()


@st.fragment(run_every="1s")
def _burbuja_en_vivo(usuario_id: str, turno_id: str) -> None:
    """Respuesta que se está escribiendo, con cronómetro. Se refresca sola cada segundo (solo este
    bloque, no la página). Cuando el turno termina, refresca la app entera para incorporar la respuesta."""
    t = turnos.turno_de(usuario_id)
    if t is None or t.id != turno_id or t.terminado:
        st.rerun(scope="app")
    t.ui_viva = time.time()   # la interfaz lo está mostrando: el aviso final nacerá ya leído
    with st.chat_message("assistant"):
        st.html(
            "<div class='ag-live'><span class='ag-dot'></span>"
            f"<span class='ag-fase'>{escape(t.fase)}</span>"
            f"<span class='ag-reloj'>⏱ {turnos.formatear_reloj(t.duracion)}</span></div>"
        )
        # Detener: avisa al agente y se detiene en cuanto emita su siguiente evento (ver core/turnos.py).
        if t.cancelar_solicitado:
            st.button("Deteniendo…", key=f"agc_stop_{turno_id}", icon=":material/hourglass_top:", disabled=True)
        elif st.button("Detener", key=f"agc_stop_{turno_id}", icon=":material/stop_circle:",
                       help="Detiene la consulta en curso"):
            turnos.cancelar(usuario_id)
            st.rerun(scope="fragment")
        if t.texto.strip():
            st.markdown(t.texto + "▌")


def _chat_agente() -> None:
    # --- ZONA DE CHAT INFERIOR: AGENTE (core.agente.Agente) ---
    uid = _usuario_id()

    if "mensajes_ui" not in st.session_state:
        st.session_state.mensajes_ui = [{"role": "assistant", "content": _SALUDO}]

    agente, error_agente = _obtener_agente()

    # El turno del agente corre en segundo plano (core/turnos.py): no se corta al cambiar de sección.
    turno = turnos.turno_de(uid)
    en_curso = turno is not None and not turno.terminado
    vistos = st.session_state.setdefault("_turnos_vistos", set())
    if turno is not None and turno.id not in vistos and (en_curso or not turno.recogido):
        # Turno que esta sesión no conocía (p. ej. recargaste la página): se muestra su pregunta.
        st.session_state.mensajes_ui.append({"role": "user", "content": turno.prompt})
        vistos.add(turno.id)
    if turno is not None and turno.terminado and not turno.recogido:
        # Terminó mientras estabas en otra sección: la respuesta pasa al chat y su aviso queda leído.
        st.session_state.mensajes_ui.append({
            "role": "assistant", "content": turno.respuesta_final(),
            "herramientas": list(turno.herramientas), "imagenes": list(turno.imagenes), "pie": turno.pie,
        })
        turnos.recoger(uid, turno.id)

    col_perfil, col_reset, _relleno = st.columns([2, 2, 4])
    with col_perfil:
        perfiles = list(getattr(config, "PERFILES", []) or [])
        if agente is not None and perfiles:
            if st.session_state.get("perfil_agente") not in perfiles:
                actual = agente.perfil or getattr(config, "PERFIL_POR_DEFECTO", None)
                st.session_state["perfil_agente"] = actual if actual in perfiles else perfiles[0]
            st.selectbox(
                "Perfil", perfiles, key="perfil_agente", on_change=_cambiar_perfil,
                label_visibility="collapsed", help="Perfil activo del agente", disabled=en_curso,
            )
    with col_reset:
        if st.button("Nueva conversación", icon=":material/refresh:", key="agc_nueva", width="stretch",
                     disabled=en_curso):
            if agente is not None:
                agente.reiniciar()
            st.session_state.mensajes_ui = [{"role": "assistant", "content": _SALUDO}]
            st.rerun()

    contenedor_chat_central = st.container(height=450, border=False, key="agc_scroll")
    with contenedor_chat_central:
        for mensaje in st.session_state.mensajes_ui:
            with st.chat_message(mensaje["role"]):
                st.markdown(mensaje["content"])
                for ruta in mensaje.get("imagenes", []):
                    if os.path.isfile(ruta):
                        st.image(ruta, use_container_width=True)
                if mensaje.get("pie"):
                    st.caption(mensaje["pie"])
        if en_curso and turno is not None:
            _burbuja_en_vivo(uid, turno.id)

    texto_guia = (
        "El agente está respondiendo… puedes moverte por la plataforma, te avisaremos"
        if en_curso else "Escribe tu consulta o pide un gráfico en imagen..."
    )
    if prompt_usuario := st.chat_input(texto_guia, disabled=en_curso):
        if agente is None:
            st.session_state.mensajes_ui.append({"role": "user", "content": prompt_usuario})
            st.session_state.mensajes_ui.append({"role": "assistant", "content": error_agente})
        else:
            nuevo = turnos.iniciar(uid, agente, prompt_usuario)
            if nuevo is not None:   # None = ya había un turno en curso: no se duplica el mensaje
                st.session_state.mensajes_ui.append({"role": "user", "content": prompt_usuario})
                vistos.add(nuevo.id)
        st.rerun(scope="app")
