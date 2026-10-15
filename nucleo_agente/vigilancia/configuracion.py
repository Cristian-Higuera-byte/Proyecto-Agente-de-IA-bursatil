"""Configuración de la vigilancia automática: intervalos, límites, estados y herramientas excluidas."""
from __future__ import annotations


INTERVALO_DEFECTO_MIN = 15       # cada cuánto se analiza el activo
INTERVALO_MIN, INTERVALO_MAX = 5, 240
DURACION_DEFECTO_H = 8.0         # la vigilancia termina sola a las N horas de autorizarla
DURACION_MIN_H, DURACION_MAX_H = 0.5, 24.0
MAX_OPERACIONES_DEFECTO = 3      # aperturas máximas por vigilancia
MAX_OPERACIONES_TOPE = 10
RIESGO_DEFECTO_PCT = 0.5         # % del equity por operación si el usuario no indica otro
MAX_VIGILANCIAS_POR_USUARIO = 3  # activas + pendientes de autorizar (acota el gasto de tokens)
MAX_ABIERTAS_POR_VIGILANCIA = 1  # no se acumulan posiciones: una abierta a la vez
ERRORES_SEGUIDOS_MAX = 3         # tras N fallos seguidos del análisis, la vigilancia se detiene
ESPERA_MOTOR_S = 20              # cada cuánto despierta el motor
PERFIL_VIGILANCIA: str | None = None   # None = perfil por defecto del agente (config.PERFIL_POR_DEFECTO)

NOMBRE_HILO_MOTOR = "pj-vigilancia-motor"
PREFIJO_HILO_CHEQUEO = "pj-vigilancia-"

# Estados
PENDIENTE, ACTIVA = "PENDIENTE_AUTORIZACION", "ACTIVA"
FINALIZADA, CANCELADA, EXPIRADA, ERROR = "FINALIZADA", "CANCELADA", "EXPIRADA", "ERROR"
VIGENTES = (PENDIENTE, ACTIVA)

# Herramientas que el análisis automático NO puede usar (ninguna ejecuta o programa órdenes).
HERRAMIENTAS_EXCLUIDAS = frozenset({
    "proponer_orden", "proponer_cierre_posicion", "proponer_vigilancia", "detener_vigilancia", "ver_vigilancias",
})
