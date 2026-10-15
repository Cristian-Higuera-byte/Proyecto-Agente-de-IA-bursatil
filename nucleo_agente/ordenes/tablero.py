"""API para el DASHBOARD: listar, rechazar y confirmar (ÚNICO punto que envía órdenes a MT5)."""
from datetime import datetime, timedelta
from typing import Any

from nucleo_agente.ordenes.base_datos import _ahora, _consultar, _ejecutar
from nucleo_agente.ordenes.envio import _enviar_apertura, _enviar_cierre


def expirar_vencidas() -> None:
    """Marca como vencidas las propuestas pendientes que ya pasaron su hora y recupera las atascadas."""
    # Una orden "EJECUTANDO" mucho después de su vencimiento quedó a medias (se cayó la app al enviarla).
    # No se asume que falló: se avisa para que el usuario lo compruebe en MT5.
    limite = (datetime.now() - timedelta(seconds=60)).isoformat(timespec="seconds")
    _ejecutar(
        "UPDATE ordenes SET estado = 'ERROR', detalle = ? WHERE estado = 'EJECUTANDO' AND expira <= ?",
        ("Envío interrumpido: revisa en MetaTrader 5 si la orden llegó a abrirse o cerrarse.", limite),
    )
    _ejecutar("UPDATE ordenes SET estado = 'EXPIRADA' WHERE estado = 'PENDIENTE' AND expira <= ?", (_ahora(),))


def listar_pendientes() -> list[dict[str, Any]]:
    expirar_vencidas()
    return _consultar(
        "SELECT * FROM ordenes WHERE estado = 'PENDIENTE' AND COALESCE(origen, 'agente') != 'automatica' "
        "ORDER BY creada, rowid"
    )


def listar_historial(limite: int = 15) -> list[dict[str, Any]]:
    return _consultar("SELECT * FROM ordenes ORDER BY creada DESC, rowid DESC LIMIT ?", (int(limite),))


def rechazar_orden(id_orden: str) -> bool:
    return _ejecutar(
        "UPDATE ordenes SET estado = 'RECHAZADA_USUARIO' WHERE id = ? AND estado = 'PENDIENTE'", (id_orden,)
    ) == 1


def confirmar_orden(id_orden: str) -> dict[str, Any]:
    """ÚNICO punto que envía órdenes a MT5. Solo lo llama el botón Confirmar del dashboard."""
    # Se "reclama" la propuesta de forma atómica: si ya se ejecutó, venció o fue rechazada, no se repite.
    reclamada = _ejecutar(
        "UPDATE ordenes SET estado = 'EJECUTANDO' WHERE id = ? AND estado = 'PENDIENTE' AND expira > ?",
        (id_orden, _ahora()),
    )
    if reclamada == 0:
        filas = _consultar("SELECT estado FROM ordenes WHERE id = ?", (id_orden,))
        if not filas:
            return {"ok": False, "mensaje": "La orden no existe."}
        if filas[0]["estado"] == "PENDIENTE":
            _ejecutar("UPDATE ordenes SET estado = 'EXPIRADA' WHERE id = ? AND estado = 'PENDIENTE'", (id_orden,))
            return {"ok": False, "mensaje": "La propuesta venció. Pídele al agente que la genere de nuevo."}
        return {"ok": False, "mensaje": f"La orden ya está en estado {filas[0]['estado']}; no se vuelve a ejecutar."}

    o = _consultar("SELECT * FROM ordenes WHERE id = ?", (id_orden,))[0]
    try:
        res = _enviar_apertura(o) if o["accion"] == "abrir" else _enviar_cierre(o)
    except Exception as e:  # noqa: BLE001
        res = {"ok": False, "estado": "ERROR", "mensaje": f"Error inesperado (revisa MT5 por si la orden se envió): {e}"}

    _ejecutar(
        "UPDATE ordenes SET estado = ?, detalle = ?, ticket_resultado = ? WHERE id = ?",
        ("EJECUTADA" if res["ok"] else res.get("estado", "ERROR"), res["mensaje"], res.get("ticket"), id_orden),
    )
    return res
