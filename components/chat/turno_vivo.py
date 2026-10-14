"""Burbuja de la respuesta que el agente está escribiendo, con cronómetro y botón Detener."""
from __future__ import annotations

import time
from html import escape

import streamlit as st

from core import turnos


@st.fragment(run_every="1s")
def burbuja_en_vivo(usuario_id: str, turno_id: str) -> None:
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
