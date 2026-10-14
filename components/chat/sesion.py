"""Sesión del chat: quién es el usuario, qué agente usa y con qué perfil."""
from __future__ import annotations

import streamlit as st

from core import turnos
from core.agente import Agente  # type: ignore[import-untyped]

SALUDO = (
    "¡Hola! Estoy listo. Pregúntame sobre cualquier activo, mercado o "
    "pídeme gráficos y su respectiva imagen renderizada."
)


def usuario_id() -> str:
    """Id del usuario con sesión iniciada: clave del turno en segundo plano y de las notificaciones."""
    return str((st.session_state.get("usuario_info") or {}).get("id") or "local")


def obtener_agente():
    """Devuelve (agente, mensaje_error). Un agente por usuario: sobrevive a recargas de la página,
    así un turno en curso y la conversación no se pierden."""
    agente = st.session_state.get("agente_ia")
    if agente is not None:
        return agente, ""
    uid = usuario_id()
    agente = turnos.agente_de(uid)
    if agente is None:
        try:
            agente = Agente(usuario_id="local")  # cambiar si el dashboard tiene login
        except Exception as e:
            return None, f"No se pudo iniciar el agente: {e}"
        turnos.registrar_agente(uid, agente)
    st.session_state["agente_ia"] = agente
    return agente, ""


def cambiar_perfil():
    agente = st.session_state.get("agente_ia")
    if agente is not None:
        agente.perfil = st.session_state["perfil_agente"]
