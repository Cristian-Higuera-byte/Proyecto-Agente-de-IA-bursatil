"""Historial del chat: une el turno en segundo plano con la conversación de la sesión y pinta los mensajes."""
from __future__ import annotations

import os

import streamlit as st

from components.chat.sesion import SALUDO
from components.chat.turno_vivo import burbuja_en_vivo
from core import turnos


def iniciar_conversacion() -> None:
    if "mensajes_ui" not in st.session_state:
        st.session_state.mensajes_ui = [{"role": "assistant", "content": SALUDO}]


def reiniciar_conversacion() -> None:
    st.session_state.mensajes_ui = [{"role": "assistant", "content": SALUDO}]


def sincronizar_turno(uid: str):
    """El turno del agente corre en segundo plano (core/turnos.py): no se corta al cambiar de sección.
    Trae a la conversación lo que pasó mientras no mirabas. Devuelve (turno, en_curso, vistos)."""
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
    return turno, en_curso, vistos


def pintar_mensajes(uid: str, turno, en_curso: bool) -> None:
    """Zona con scroll: mensajes guardados y, si hay un turno en curso, su burbuja en vivo."""
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
            burbuja_en_vivo(uid, turno.id)
