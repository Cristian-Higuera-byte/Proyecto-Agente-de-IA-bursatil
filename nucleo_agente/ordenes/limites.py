"""Límites de riesgo del agente. Edítalos aquí; el agente no puede cambiarlos (no están en el prompt)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class LimitesRiesgo:
    solo_demo: bool = True                       # rechaza TODO si la cuenta conectada no es demo
    riesgo_max_por_operacion_pct: float = 1.0    # % del equity que se puede perder si salta el SL
    riesgo_max_total_pct: float = 3.0            # % del equity en riesgo sumando posiciones abiertas + propuestas pendientes + la nueva
    max_posiciones_abiertas: int = 3
    perdida_max_diaria_pct: float = 3.0          # % del balance; al alcanzarlo no se abren más
    volumen_max: float = 0.5                     # lotes máximos por orden
    vigencia_propuesta_min: int = 10             # minutos antes de que una propuesta venza
    desviacion_puntos: int = 20                  # deslizamiento máximo aceptado al ejecutar
    # Símbolos que el agente puede operar. None = CUALQUIER activo disponible en MT5 (el nombre se traduce
    # al del bróker con resolver_simbolo: XAUUSD <-> GOLD, sufijos .m / ..., etc.). Para restringirlo pon
    # una tupla, por ejemplo ("EURUSD", "GBPUSD", "GOLD").
    simbolos_permitidos: tuple | None = None
    # Lista negra opcional: símbolos que NUNCA se operan aunque existan en MT5.
    simbolos_bloqueados: tuple = ()


LIMITES = LimitesRiesgo()

MAGIC = 940731  # identifica en MT5 las órdenes enviadas desde este módulo
TOLERANCIA_RIESGO = 1.10  # al confirmar, el precio pudo moverse: se tolera hasta +10 % sobre el límite
TOLERANCIA_VS_PROPUESTA = 1.25  # al confirmar, el riesgo real no puede superar en más de 25 % lo que vio el usuario
