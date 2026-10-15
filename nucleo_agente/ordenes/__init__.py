"""Órdenes del agente - FASE 1: el agente PROPONE, el usuario CONFIRMA.

NOMBRE DEL PAQUETE: nucleo_agente/ordenes

Garantías de diseño:
  * El agente NO tiene ninguna herramienta que ejecute órdenes. Solo llama a
    proponer_apertura / proponer_cierre (ver herramientas_agente/ordenes_herramientas), que
    validan contra LIMITES y guardan una propuesta PENDIENTE.
  * La única función que envía algo a MetaTrader 5 es confirmar_orden(), y solo la
    llama el botón "Confirmar" del dashboard (componentes_plataforma/panel_ordenes.py).
  * Los límites de riesgo están en código (LIMITES), no en el prompt: el modelo no
    puede saltárselos ni cambiarlos.
  * Cada propuesta queda registrada en SQLite (data/ordenes.db) con su justificación:
    es el registro de auditoría de todo lo que el agente decidió.
  * Una propuesta solo se ejecuta una vez (se "reclama" de forma atómica), así que
    un doble clic o un reintento no duplica la orden.

Archivos: limites.py (LIMITES), db.py + sql/ (SQLite), mt5_utiles.py, validacion.py, propuestas.py (API del agente),
envio.py (órdenes a MT5) y dashboard.py (listar / rechazar / confirmar). Aquí se reexportan todos los nombres que
tenía el módulo único (incluidos los privados que usan vigilancia.py y las herramientas) para que
`from nucleo_agente import ordenes` y `ordenes.confirmar_orden(...)` sigan funcionando igual."""
from nucleo_agente.ordenes.limites import (
    LIMITES,
    LimitesRiesgo,
    MAGIC,
    TOLERANCIA_RIESGO,
    TOLERANCIA_VS_PROPUESTA,
)  # noqa: F401
from nucleo_agente.ordenes.base_datos import (
    DIR_DATOS,
    RUTA_DB,
    kill_switch_activo,
    set_kill_switch,
    _COLUMNAS_NUEVAS_ORDENES,
    _DB_LOCK,
    _SQL_ORDENES,
    _SQL_VIGILANCIAS,
    _ahora,
    _conectar,
    _consultar,
    _ejecutar,
    _insertar,
)  # noqa: F401
from nucleo_agente.ordenes.mt5_utiles import (
    MT5_LOCK,
    inicializar_mt5,
    mt5,
    resolver_simbolo,
    _chequeos_globales,
    _con_lock,
    _desviacion,
    _inicio_dia_servidor,
    _modo_llenado,
    _normalizar,
    _perdida_del_dia,
    _preparar_mt5,
    _resolver_simbolo,
    _riesgo_expuesto,
    _simbolos_para_reloj,
)  # noqa: F401
from nucleo_agente.ordenes.validacion import (
    cuenta_demo,
    validar_simbolo,
    _evaluar_apertura,
)  # noqa: F401
from nucleo_agente.ordenes.propuestas import (
    estado_riesgo,
    proponer_apertura,
    proponer_cierre,
    resumen_posiciones,
    _propuesta_pendiente,
    _respuesta_duplicada,
)  # noqa: F401
from nucleo_agente.ordenes.envio import (
    _enviar_apertura,
    _enviar_cierre,
    _interpretar,
)  # noqa: F401
from nucleo_agente.ordenes.tablero import (
    confirmar_orden,
    expirar_vencidas,
    listar_historial,
    listar_pendientes,
    rechazar_orden,
)  # noqa: F401
