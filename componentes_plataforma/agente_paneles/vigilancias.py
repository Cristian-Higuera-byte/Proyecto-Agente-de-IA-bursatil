"""Vigilancias automáticas: tarjetas del panel derecho (pendientes de autorizar y activas)."""
from typing import Any

import streamlit as st

from componentes_plataforma.agente_paneles.datos import CLAVE_AVISO
from componentes_plataforma.agente_paneles.formato import esc, hora, kv
from nucleo_agente import vigilancia


def usuario_id() -> str:
    return str((st.session_state.get("usuario_info") or {}).get("id") or "local")


def tarjeta_vigilancia(v: dict[str, Any]) -> str:
    pendiente = v["estado"] == vigilancia.PENDIENTE
    ops = f"{v.get('operaciones') or 0}/{v['max_operaciones']}"
    if pendiente:
        tiempo = f"Autoriza antes de las {hora(v.get('expira_autorizacion'))}"
        badge = ("<span class='ag-badge' style='color:#f0b90b;border-color:#f0b90b55;background:#f0b90b18'>"
                 "Pendiente de autorizar</span>")
        cuarto = kv("Dura", f"{v['duracion_horas']:g} h")
        pie = (f"<div class='ag-aviso'>El agente analizará <b>{esc(v['simbolo'])}</b> y, si autorizas, "
               "<b>comprará o venderá solo</b>, sin pedirte confirmación, dentro de estos límites. "
               "Solo cuenta demo; puedes detenerla cuando quieras.</div>")
        cita = esc((v.get("instruccion") or "").strip())
    else:
        tiempo = f"Vence a las {hora(v.get('vence'))}"
        badge = ("<span class='ag-badge' style='color:#2ebd85;border-color:#2ebd8555;background:#2ebd8518'>"
                 "Activa</span>")
        cuarto = kv("Chequeos", str(v.get("chequeos") or 0))
        ultimo = hora(v["ultimo_chequeo"]) if v.get("ultimo_chequeo") else "—"
        pie = (f"<div class='ag-aviso'>Último chequeo {ultimo} · próximo {hora(v.get('proximo_chequeo'))}</div>")
        cita = esc((v.get("ultimo_resumen") or "Aún sin chequeos.").strip())
    datos = (kv("Riesgo/op.", f"{v['riesgo_pct']:g}%") + kv("Operaciones", ops)
             + kv("Cada", f"{v['intervalo_min']} min") + cuarto)
    return (
        "<div class='ag-row'>"
        f"<div class='ag-top'><span class='ag-t'>{esc(tiempo)}</span>{badge}</div>"
        f"<div class='ag-main'><span class='auto'>VIGILANCIA</span> · {esc(v['simbolo'])}</div>"
        f"<div class='ag-grid'>{datos}</div>{pie}"
        + (f"<div class='ag-quote'>{cita}</div>" if cita else "")
        + "</div>"
    )


def seccion_vigilancias(uid: str) -> None:
    for v in vigilancia.listar(uid):
        with st.container(key=f"agp_card_auto_{v['id']}"):
            st.html(tarjeta_vigilancia(v))
            if v["estado"] == vigilancia.PENDIENTE:
                if st.button("Autorizar vigilancia", key=f"agp_ok_vig_{v['id']}", icon=":material/check:",
                             type="primary", width="stretch"):
                    res = vigilancia.autorizar(v["id"], uid)
                    st.session_state[CLAVE_AVISO] = ("ok" if res["ok"] else "error", res["mensaje"])
                    st.rerun(scope="app")
                if st.button("Rechazar", key=f"agp_no_vig_{v['id']}", width="stretch"):
                    vigilancia.rechazar(v["id"], uid)
                    st.rerun(scope="app")
            else:
                if st.button("Detener vigilancia", key=f"agp_no_stopvig_{v['id']}",
                             icon=":material/stop_circle:", width="stretch"):
                    st.session_state[CLAVE_AVISO] = ("ok", vigilancia.detener(uid, vid=v["id"])["mensaje"])
                    st.rerun(scope="app")
