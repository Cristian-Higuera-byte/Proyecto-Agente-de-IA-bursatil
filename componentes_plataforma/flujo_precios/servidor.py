"""Estado del servidor de datos (servidor_datos.py) e intervalo de los fragmentos `run_every`."""
import os
import urllib.request

import streamlit as st

API_URL = os.environ.get("MT5_API_URL", "http://localhost:8000")


@st.cache_data(ttl=15, show_spinner=False)
def feed_activo() -> bool:
    """True si servidor_datos.py responde (se revisa como máximo cada 15 s)."""
    try:
        with urllib.request.urlopen(API_URL + "/salud", timeout=0.4) as r:
            return r.status == 200
    except Exception:
        return False


def intervalo(rapido: str = "2s", lento: str | None = None) -> str | None:
    """Intervalo de los fragmentos `run_every`. Con feed en vivo, por defecto
    NINGUNO (None): el feed ya pinta todo y cada recarga de Streamlit atenúa el
    bloque un instante (parpadeo). Los fragmentos se siguen recargando al
    interactuar (✕, +, botones). Sin feed, el refresco rápido de siempre."""
    return lento if feed_activo() else rapido
