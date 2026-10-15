"""Panel del chat del agente: tarjeta con selector de perfil, «Nueva conversación», historial y caja de texto."""
from __future__ import annotations

import streamlit as st

import configuracion
from componentes_plataforma.chat.historial import (iniciar_conversacion, pintar_mensajes, reiniciar_conversacion,
                                       sincronizar_turno)
from componentes_plataforma.chat.sesion import cambiar_perfil, obtener_agente, usuario_id
from componentes_plataforma.panel_ordenes import cabecera_agente
from nucleo_agente import turnos


def renderizar_chat_agente() -> None:
    """Chat del agente. Va en la fila de abajo de aplicacion.py, junto al historial y las propuestas."""
    with st.container(key="agc_panel"):   # tarjeta con el mismo estilo que el historial y las propuestas
        st.html(cabecera_agente(
            "smart_toy", "Agente IA Analítico",
            "Consola, gráficos e imágenes · mantiene el contexto y usa las herramientas de MT5",
        ))
        _chat_agente()


def _controles(agente, en_curso: bool) -> None:
    """Fila superior: selector de perfil y botón «Nueva conversación»."""
    col_perfil, col_reset, _relleno = st.columns([2, 2, 4])
    with col_perfil:
        perfiles = list(getattr(configuracion, "PERFILES", []) or [])
        if agente is not None and perfiles:
            if st.session_state.get("perfil_agente") not in perfiles:
                actual = agente.perfil or getattr(configuracion, "PERFIL_POR_DEFECTO", None)
                st.session_state["perfil_agente"] = actual if actual in perfiles else perfiles[0]
            st.selectbox(
                "Perfil", perfiles, key="perfil_agente", on_change=cambiar_perfil,
                label_visibility="collapsed", help="Perfil activo del agente", disabled=en_curso,
            )
    with col_reset:
        if st.button("Nueva conversación", icon=":material/refresh:", key="agc_nueva", width="stretch",
                     disabled=en_curso):
            if agente is not None:
                agente.reiniciar()
            reiniciar_conversacion()
            st.rerun()


def _entrada(uid: str, agente, error_agente: str, en_curso: bool, vistos) -> None:
    """Caja de texto: lanza el turno en segundo plano (o muestra el error si no hay agente)."""
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


def _chat_agente() -> None:
    # --- ZONA DE CHAT INFERIOR: AGENTE (nucleo_agente.agente.Agente) ---
    uid = usuario_id()
    iniciar_conversacion()
    agente, error_agente = obtener_agente()
    turno, en_curso, vistos = sincronizar_turno(uid)
    _controles(agente, en_curso)
    pintar_mensajes(uid, turno, en_curso)
    _entrada(uid, agente, error_agente, en_curso, vistos)
