"""Panel IZQUIERDO: historial permanente de cada orden que el agente propuso, ejecutó o se bloqueó."""
from typing import Any

import streamlit as st

from componentes_plataforma.agente_paneles.datos import ESTADOS
from componentes_plataforma.agente_paneles.formato import cabecera_agente, clase_lado, detalle, esc, hora, marca_auto, titulo, vacio
from nucleo_agente import ordenes


def fila_historial(o: dict[str, Any]) -> str:
    estado = str(o.get("estado") or "")
    etiqueta, color = ESTADOS.get(estado, (estado or "Desconocido", "#8b949e"))
    return (
        f"<div class='ag-row {clase_lado(o)}'>"
        f"<div class='ag-top'><span class='ag-t'>{hora(o.get('creada'))}{marca_auto(o)}</span>"
        f"<span class='ag-badge' style='color:{color};border-color:{color}55;background:{color}18'>"
        f"{esc(etiqueta)}</span></div>"
        f"<div class='ag-main'>{titulo(o)}</div>{detalle(o)}</div>"
    )


def renderizar_historial_agente(limite: int = 30, altura: int = 300) -> None:
    try:
        ordenes.expirar_vencidas()  # marca como vencidas las propuestas que ya expiraron
        historial = ordenes.listar_historial(limite)
    except Exception as e:  # noqa: BLE001
        st.warning(f"No se pudo leer el historial del agente: {e}")
        return

    with st.container(key="agh_panel"):
        st.html(cabecera_agente("history", "Historial del agente", "Cada orden que propone, ejecuta o se bloquea."))
        with st.container(height=altura, border=False, key="agh_scroll"):
            if not historial:
                st.html(vacio("history", "Aún no hay órdenes registradas."))
            else:
                st.html("".join(fila_historial(o) for o in historial))
