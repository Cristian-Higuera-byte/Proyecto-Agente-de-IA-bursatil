"""Prompt de sistema del agente (prompts/sistema.md; con respaldo si el archivo no existe)."""
from __future__ import annotations

from datetime import datetime

import configuracion

PROMPT_RESPALDO = (
    "Eres un analista bursátil. Hoy es {fecha}. Usa las herramientas para obtener datos "
    "reales, no inventes cifras y responde siempre en español."
)


def _prompt_sistema(contexto: str = "") -> str:
    ruta = configuracion.DIR_PROMPTS / "sistema.md"
    base = ruta.read_text(encoding="utf-8") if ruta.exists() else PROMPT_RESPALDO
    # Solo la fecha (no la hora): así el prefijo del prompt no cambia durante el día
    # y DeepSeek puede reutilizar su caché de contexto (más barato y rápido).
    prompt = base.replace("{fecha}", datetime.now().astimezone().strftime("%Y-%m-%d"))
    return f"{prompt}\n\n{contexto}" if contexto else prompt
