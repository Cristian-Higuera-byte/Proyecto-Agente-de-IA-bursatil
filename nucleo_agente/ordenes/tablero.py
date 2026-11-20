# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ------------------------------------ INICIO Piña y Jara tablero .PY -----------------------------------
# -------------------------------------------------------------------------------------------------------

"""API para el DASHBOARD: listar, rechazar y confirmar (ÚNICO punto que envía órdenes a MT5).

Lo usa el panel de órdenes (componentes_plataforma/agente_paneles/) y el motor de vigilancia. Todas las
transiciones de estado se hacen con UPDATE condicionales para que cada propuesta se procese una sola vez."""
from datetime import datetime, timedelta
from typing import Any

from herramientas import idempotencia_ordenes
from nucleo_agente.ordenes.base_datos import _ahora, _consultar, _ejecutar, condicion_dueno
from nucleo_agente.ordenes.envio import _enviar_apertura, _enviar_cierre
from nucleo_agente.ordenes.mt5_utiles import NOMBRE_BROKER


# TITULO EXPIRAR VENCIDAS

def expirar_vencidas() -> None:
    """Marca como vencidas las propuestas pendientes que ya pasaron su hora y recupera las atascadas.

    Efectos: dos UPDATE sobre SQLite. Las órdenes EJECUTANDO vencidas hace más de 60 s pasan a ERROR con un
    aviso; las PENDIENTE vencidas pasan a EXPIRADA."""
    # Una orden "EJECUTANDO" mucho después de su vencimiento quedó a medias (se cayó la app al enviarla).
    # No se asume que falló: se avisa para que el usuario lo compruebe en MT5.
    # Umbral: 60 s de gracia tras la expiración antes de dar por interrumpido un envío en curso.
    limite = (datetime.now() - timedelta(seconds=60)).isoformat(timespec="seconds")
    # Las órdenes que quedaron a medias pasan a ERROR (no se asume que fallaron).
    _ejecutar(
        "UPDATE ordenes SET estado = 'ERROR', detalle = ? WHERE estado = 'EJECUTANDO' AND expira <= ?",
        (f"Envío interrumpido: revisa en {NOMBRE_BROKER} si la orden llegó a abrirse o cerrarse.", limite),
    )
    # Las propuestas pendientes cuya vigencia terminó pasan a EXPIRADA.
    _ejecutar("UPDATE ordenes SET estado = 'EXPIRADA' WHERE estado = 'PENDIENTE' AND expira <= ?", (_ahora(),))


# TITULO LISTAR PENDIENTES

def listar_pendientes() -> list[dict[str, Any]]:
    """Devuelve las propuestas PENDIENTE que debe confirmar el usuario, de la más antigua a la más reciente.

    Antes expira las vencidas. Excluye las de origen 'automatica' (las gestiona el motor de vigilancia). Solo las del usuario y la cuenta actuales."""
    expirar_vencidas()
    dueno, valores = condicion_dueno()
    return _consultar(
        "SELECT * FROM ordenes WHERE estado IN ('PENDIENTE', 'VERIFICANDO') AND COALESCE(origen, 'agente') != 'automatica'" + dueno + " ORDER BY creada, rowid", valores
    )


# TITULO LISTAR HISTORIAL

def listar_historial(limite: int = 15) -> list[dict[str, Any]]:
    """Devuelve las últimas `limite` órdenes de cualquier estado del usuario y la cuenta actuales, de la más reciente a la más antigua."""
    dueno, valores = condicion_dueno()
    return _consultar("SELECT * FROM ordenes WHERE 1 = 1" + dueno + " ORDER BY creada DESC, rowid DESC LIMIT ?", (*valores, int(limite)))


# TITULO RECHAZAR ORDEN

def rechazar_orden(id_orden: str) -> bool:
    """Marca como RECHAZADA_USUARIO una propuesta PENDIENTE del usuario y la cuenta actuales. Devuelve True si cambió exactamente una fila.

    Una propuesta de otro usuario (o de la otra cuenta) no se toca: se responde igual que si no existiera."""
    dueno, valores = condicion_dueno()
    return _ejecutar(
        "UPDATE ordenes SET estado = 'RECHAZADA_USUARIO' WHERE id = ? AND estado = 'PENDIENTE'" + dueno, (id_orden, *valores)
    ) == 1


# TITULO RESULTADO PREVIO

def _resultado_previo(o: dict[str, Any]) -> dict[str, Any] | None:
    """Si esta propuesta de apertura ya tuvo un intento de envío (su clave existe), devuelve su desenlace SIN volver a validar ni enviar; si nunca se intentó, devuelve None.

    Sirve cuando la confirmación anterior quedó incierta (el bróker no confirmó): al confirmar de nuevo no se revalida el riesgo (la posición ya pudo abrirse y alterar los
    cálculos) ni se abre otra orden; se consulta al bróker qué pasó con la primera. Devuelve el diccionario de `_interpretar` ({ok, mensaje, ticket | estado})."""
    from herramientas import paradas_emergencia
    dueno = paradas_emergencia.dueno_actual()
    if o["accion"] != "abrir" or dueno is None:
        return None
    fila = idempotencia_ordenes.leer(f"{dueno[0]}:{dueno[1]}:propuesta:{o['id']}")
    if fila is None:
        return None
    resultado = idempotencia_ordenes.resultado_guardado(fila)
    if resultado is None:
        from herramientas.backends import sesiones_capital
        modulo = sesiones_capital.modulo_actual()
        resultado = modulo._reconciliar(fila) if hasattr(modulo, "_reconciliar") else {"error": "Verificando con el bróker.", "incierto": True}
    if resultado.get("incierto"):
        return {"ok": False, "estado": "VERIFICANDO", "mensaje": resultado["error"]}
    if "error" in resultado:
        return {"ok": False, "estado": "ERROR", "mensaje": str(resultado["error"])}
    return {"ok": True, "ticket": resultado.get("order"), "mensaje": f"Ejecutado: {o['lado']} {o['volumen']} {o['simbolo']} a {resultado.get('price')}."}


# TITULO CONFIRMAR ORDEN

def confirmar_orden(id_orden: str) -> dict[str, Any]:
    """ÚNICO punto que envía órdenes a MT5. Solo lo llama el botón Confirmar del dashboard (y el motor de
    vigilancia para las operaciones automáticas autorizadas).

    Reclama la propuesta de forma atómica (PENDIENTE a EJECUTANDO) para que un doble clic no duplique la orden,
    envía la apertura o el cierre y guarda el estado final. Devuelve un diccionario con `ok`, `mensaje` y,
    si hubo ejecución, `ticket`; si la orden no existe, venció o ya se procesó, devuelve `ok` False sin enviar nada.

    Solo confirma propuestas del usuario y la cuenta actuales: el dueño y la cuenta van en la misma sentencia atómica que reclama la propuesta, así que la de otro
    usuario, o la creada en la otra cuenta (demo/real), responde «La orden no existe» y no llega al bróker. La orden se envía con la cuenta con la que se creó."""
    dueno, valores = condicion_dueno()
    # Paso 1: se "reclama" la propuesta de forma atómica: si ya se ejecutó, venció o fue rechazada, no se repite. Una orden AUTOMÁTICA solo se reclama si su vigilancia sigue activa y vigente
    # (V19): se comprueba en la misma sentencia, así que detener la vigilancia entre la propuesta y el envío cancela el envío.
    reclamada = _ejecutar(
        "UPDATE ordenes SET estado = 'EJECUTANDO' WHERE id = ? AND ((estado = 'PENDIENTE' AND expira > ?) OR estado = 'VERIFICANDO')"
        " AND (COALESCE(origen, 'agente') <> 'automatica' OR vigilancia_id IN "
        "(SELECT id FROM vigilancias WHERE estado = 'ACTIVA' AND (vence IS NULL OR vence > ?)))" + dueno,
        (id_orden, _ahora(), _ahora(), *valores),
    )
    if reclamada == 0:
        # No se pudo reclamar: se averigua por qué para dar un mensaje preciso (solo entre las propias: una ajena es «no existe»).
        filas = _consultar("SELECT estado, expira FROM ordenes WHERE id = ?" + dueno, (id_orden, *valores))
        if not filas:
            return {"ok": False, "mensaje": "La orden no existe."}
        if filas[0]["estado"] == "PENDIENTE" and filas[0]["expira"] > _ahora():
            # Vigente pero no reclamable: es una orden automática y su vigilancia ya no está activa (V19). No se envía y no queda colgada.
            _ejecutar("UPDATE ordenes SET estado = 'RECHAZADA_USUARIO', detalle = ? WHERE id = ? AND estado = 'PENDIENTE'" + dueno,
                      ("La vigilancia que la generó ya no estaba activa: no se envió.", id_orden, *valores))
            return {"ok": False, "mensaje": "La vigilancia que generó esta orden ya no está activa: no se envió."}
        if filas[0]["estado"] == "PENDIENTE":
            # Seguía PENDIENTE pero vencida: se marca EXPIRADA.
            _ejecutar("UPDATE ordenes SET estado = 'EXPIRADA' WHERE id = ? AND estado = 'PENDIENTE'" + dueno, (id_orden, *valores))
            return {"ok": False, "mensaje": "La propuesta venció. Pídele al agente que la genere de nuevo."}
        return {"ok": False, "mensaje": f"La orden ya está en estado {filas[0]['estado']}; no se vuelve a ejecutar."}

    # Paso 2: se envía a MT5 según la acción guardada (abrir o cerrar).
    o = _consultar("SELECT * FROM ordenes WHERE id = ?" + dueno, (id_orden, *valores))[0]
    try:
        # Clave de idempotencia = la propuesta: si el resultado quedó incierto y se confirma de nuevo, no se abre otra orden sino que se verifica la primera.
        resultado = _resultado_previo(o)
        if resultado is None:
            with idempotencia_ordenes.con_clave(f"propuesta:{id_orden}"):
                resultado = _enviar_apertura(o) if o["accion"] == "abrir" else _enviar_cierre(o)
    except Exception as e:  # noqa: BLE001
        resultado = {"ok": False, "estado": "ERROR", "mensaje": f"Error inesperado (revisa {NOMBRE_BROKER} por si la orden se envió): {e}"}

    # Paso 3: se registra el resultado final (EJECUTADA u otro estado de fallo) y el ticket devuelto.
    _ejecutar(
        "UPDATE ordenes SET estado = ?, detalle = ?, ticket_resultado = ? WHERE id = ?" + dueno,
        ("EJECUTADA" if resultado["ok"] else resultado.get("estado", "ERROR"), resultado["mensaje"], resultado.get("ticket"), id_orden, *valores),
    )
    return resultado


# -------------------------------------------------------------------------------------------------------
# ------------------------------------- FIN Piña y Jara tablero .PY -------------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
