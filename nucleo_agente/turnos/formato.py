"""Formato de duraciones para el pie del turno y el cronómetro en vivo."""
from __future__ import annotations


def formatear_duracion(segundos: float) -> str:
    """'7 s', '1 min 12 s'..."""
    s = max(0, int(segundos))
    return f"{s} s" if s < 60 else f"{s // 60} min {s % 60:02d} s"


def formatear_reloj(segundos: float) -> str:
    """'00:07', '01:12' (para el cronómetro en vivo)."""
    s = max(0, int(segundos))
    return f"{s // 60:02d}:{s % 60:02d}"
