"""Herramientas registradas para el agente (los esquemas viven en esquemas.json)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from nucleo_agente import contexto, ordenes, vigilancia
from herramientas_agente.base import cargar_json, herramienta
from herramientas_agente.ordenes_herramientas.auxiliares import _a_numero

_ESQ = cargar_json(Path(__file__).parent / "esquemas.json")


@herramienta(**_ESQ["proponer_orden"])
def proponer_orden(
    simbolo: str,
    lado: str,
    stop_loss: float,
    justificacion: str,
    take_profit: float | None = None,
    riesgo_pct: float | None = 0.5,
) -> dict[str, Any]:
    riesgo = _a_numero(riesgo_pct)
    if riesgo in (None, ""):          # el modelo envió null o vacío: se usa el valor por defecto
        riesgo = 0.5
    if isinstance(riesgo, bool) or not isinstance(riesgo, (int, float)):
        return {"estado": "RECHAZADA", "motivo": "'riesgo_pct' debe ser un número (por ejemplo 0.5)."}
    return ordenes.proponer_apertura(
        simbolo=simbolo,
        lado=lado,
        stop_loss=_a_numero(stop_loss),
        take_profit=_a_numero(take_profit),
        riesgo_pct=riesgo,
        justificacion=justificacion,
    )


@herramienta(**_ESQ["proponer_cierre_posicion"])
def proponer_cierre_posicion(ticket: int, justificacion: str) -> dict[str, Any]:
    return ordenes.proponer_cierre(ticket=ticket, justificacion=justificacion)


@herramienta(**_ESQ["ver_posiciones"])
def ver_posiciones() -> dict[str, Any]:
    return ordenes.resumen_posiciones()


@herramienta(**_ESQ["ver_limites_riesgo"])
def ver_limites_riesgo() -> dict[str, Any]:
    return ordenes.estado_riesgo()


@herramienta(**_ESQ["proponer_vigilancia"])
def proponer_vigilancia(
    simbolo: str,
    instruccion: str,
    riesgo_pct: float | None = None,
    max_operaciones: int | None = None,
    duracion_horas: float | None = None,
    intervalo_min: int | None = None,
) -> dict[str, Any]:
    r = vigilancia.crear(
        contexto.usuario_actual(), simbolo, instruccion,
        riesgo_pct=_a_numero(riesgo_pct), max_operaciones=_a_numero(max_operaciones),
        duracion_horas=_a_numero(duracion_horas), intervalo_min=_a_numero(intervalo_min),
    )
    if not r["ok"]:
        return {"estado": "RECHAZADA", "motivo": r["motivo"]}
    return {
        "estado": "VIGILANCIA_PENDIENTE_DE_AUTORIZACION",
        "id": r["id"],
        "resumen": r["resumen"],
        "mensaje": (
            "Vigilancia registrada, pero NO está activa: el usuario debe pulsar «Autorizar» en la tarjeta del panel "
            "«Órdenes propuestas» (vale unos minutos). Hasta entonces NO se vigila ni se opera. No afirmes que ya está "
            "vigilando: resume los términos (activo, riesgo, operaciones máximas, duración, frecuencia) y dile cómo autorizarla."
        ),
    }


@herramienta(**_ESQ["detener_vigilancia"])
def detener_vigilancia(simbolo: str | None = None, id: str | None = None) -> dict[str, Any]:  # noqa: A002
    return vigilancia.detener(contexto.usuario_actual(), vid=id, simbolo=simbolo)


@herramienta(**_ESQ["ver_vigilancias"])
def ver_vigilancias() -> dict[str, Any]:
    filas = vigilancia.listar(contexto.usuario_actual(), incluir_finalizadas=True, limite=8)
    return {
        "vigilancias": [
            {**vigilancia.resumen_terminos(f), "vence": f.get("vence"), "proximo_chequeo": f.get("proximo_chequeo"),
             "ultimo_resumen": f.get("ultimo_resumen"), "detalle": f.get("detalle")}
            for f in filas
        ]
    }
