"""Motor de precios en vivo: un hilo lee ticks y cuenta de MT5 y los reparte a los clientes SSE."""
from .base import MOTOR, MotorPrecios

__all__ = ["MOTOR", "MotorPrecios"]
