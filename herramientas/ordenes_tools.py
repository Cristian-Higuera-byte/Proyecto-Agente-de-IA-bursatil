"""Herramientas del agente para operar: SOLO proponer y consultar (Fase 1).

NOMBRE DEL ARCHIVO: herramientas/ordenes_tools.py

Ninguna de estas herramientas ejecuta órdenes en MetaTrader 5. Las propuestas quedan
pendientes y el usuario las confirma con un botón en el dashboard (core/ordenes.py).
"""

from __future__ import annotations

from typing import Any

from core import ordenes
from herramientas.base import herramienta


def _a_numero(valor: Any) -> Any:
    """Los LLM a veces envían números como texto; se convierten si es posible."""
    if isinstance(valor, str):
        try:
            return float(valor.replace(",", "."))
        except ValueError:
            return valor
    return valor


@herramienta(
    descripcion=(
        "Propone abrir una operación (compra o venta) en la cuenta demo. NO la ejecuta: queda pendiente "
        "y el usuario debe confirmarla con un botón en el dashboard. Úsala solo cuando el usuario te pida "
        "una operación o autorice operar tras tu análisis; si solo pide una opinión, no propongas órdenes. "
        "El stop loss es OBLIGATORIO. No calcules el tamaño del lote: indica 'riesgo_pct' (porcentaje del "
        "equity que se perdería si salta el stop loss) y el sistema calcula el lote. Si el sistema rechaza "
        "la propuesta por riesgo, explica el motivo al usuario y, si procede, ajusta y vuelve a intentar."
    ),
    parametros={
        "simbolo": {"type": "string", "description": "Símbolo exacto en MT5 (ej. 'EURUSD', 'GOLD')."},
        "lado": {"type": "string", "enum": ["compra", "venta"], "description": "Dirección de la operación."},
        "stop_loss": {"type": "number", "description": "Precio del stop loss (obligatorio)."},
        "take_profit": {"type": "number", "description": "Precio del take profit (opcional pero recomendado)."},
        "riesgo_pct": {
            "type": "number",
            "description": "% del equity a arriesgar si salta el stop loss (ej. 0.5). Por defecto 0.5.",
        },
        "justificacion": {
            "type": "string",
            "description": "Razonamiento breve de por qué conviene esta operación (queda en el registro de auditoría).",
        },
    },
    requeridos=["simbolo", "lado", "stop_loss", "justificacion"],
    nombre="proponer_orden",
)
def proponer_orden(
    simbolo: str,
    lado: str,
    stop_loss: float,
    justificacion: str,
    take_profit: float | None = None,
    riesgo_pct: float = 0.5,
) -> dict[str, Any]:
    return ordenes.proponer_apertura(
        simbolo=simbolo,
        lado=lado,
        stop_loss=_a_numero(stop_loss),
        take_profit=_a_numero(take_profit),
        riesgo_pct=_a_numero(riesgo_pct),
        justificacion=justificacion,
    )


@herramienta(
    descripcion=(
        "Propone cerrar una posición abierta de la cuenta demo. NO la cierra: queda pendiente y el usuario "
        "debe confirmarla con un botón en el dashboard. Obtén el ticket con 'ver_posiciones'."
    ),
    parametros={
        "ticket": {"type": "integer", "description": "Ticket de la posición a cerrar."},
        "justificacion": {"type": "string", "description": "Por qué conviene cerrarla (queda en el registro)."},
    },
    requeridos=["ticket", "justificacion"],
    nombre="proponer_cierre_posicion",
)
def proponer_cierre_posicion(ticket: int, justificacion: str) -> dict[str, Any]:
    return ordenes.proponer_cierre(ticket=ticket, justificacion=justificacion)


@herramienta(
    descripcion=(
        "Consulta la cuenta de MetaTrader 5 (tipo demo/real, balance, equity, margen libre) y las posiciones "
        "abiertas con su ticket, stop loss, take profit y resultado actual."
    ),
    parametros={},
    requeridos=[],
    nombre="ver_posiciones",
)
def ver_posiciones() -> dict[str, Any]:
    return ordenes.resumen_posiciones()


@herramienta(
    descripcion=(
        "Consulta los límites de riesgo vigentes (riesgo máximo por operación, posiciones máximas, pérdida "
        "diaria máxima, símbolos permitidos) y el estado actual (pérdida del día, posiciones abiertas, "
        "interruptor de emergencia). Úsala antes de proponer una operación si dudas de qué está permitido."
    ),
    parametros={},
    requeridos=[],
    nombre="ver_limites_riesgo",
)
def ver_limites_riesgo() -> dict[str, Any]:
    return ordenes.estado_riesgo()