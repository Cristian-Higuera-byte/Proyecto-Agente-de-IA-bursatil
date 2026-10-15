"""Registro de la aceptación de los términos de One-Click Trading (por usuario, con fecha)."""
import json
import os
from datetime import datetime
from pathlib import Path

import streamlit as st

# MODO DEMO: la renuncia se muestra CADA VEZ que se activa One-Click Trading (para
# presentaciones). La aceptación se sigue registrando en _RUTA con su fecha.
# Para el uso normal (pedirla solo la primera vez), poner False.
PEDIR_SIEMPRE = True

_RUTA = os.path.join(str(Path(__file__).resolve().parents[2]), "data", "one_click_aceptaciones.json")


def _uid() -> str:
    u = st.session_state.get("usuario_info") or {}
    return str(u.get("id") or u.get("email") or "anonimo")


def _leer() -> dict:
    try:
        with open(_RUTA, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def aceptado() -> bool:
    """¿El usuario actual ya aceptó los términos de One-Click Trading?"""
    if PEDIR_SIEMPRE:
        return False
    if st.session_state.get("oct_aceptado"):
        return True
    ok = _uid() in _leer()
    if ok:
        st.session_state.oct_aceptado = True
    return ok


def registrar():
    datos = _leer()
    u = st.session_state.get("usuario_info") or {}
    datos[_uid()] = {"email": u.get("email", ""), "fecha": datetime.now().isoformat(timespec="seconds"),
                     "version_terminos": 1}
    os.makedirs(os.path.dirname(_RUTA), exist_ok=True)
    with open(_RUTA, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    st.session_state.oct_aceptado = True
