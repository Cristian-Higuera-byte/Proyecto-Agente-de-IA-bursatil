"""Parámetros de la petición a DeepSeek según el perfil (modelo, thinking, temperatura, stream)."""
from __future__ import annotations

from typing import Any

import configuracion  # type: ignore[import-not-found]


def construir_kwargs(
    nombre: str,
    mensajes: list[dict[str, Any]],
    herramientas: list[dict[str, Any]] | None,
    stream: bool,
) -> dict[str, Any]:
    p = configuracion.PERFILES[nombre]
    kw: dict[str, Any] = {
        "model": p.modelo,
        "messages": mensajes,
        "max_tokens": p.max_tokens,
    }
    if herramientas:
        kw["tools"] = herramientas
    if p.thinking:
        kw["reasoning_effort"] = p.esfuerzo
        kw["extra_body"] = {"thinking": {"type": "enabled"}}
    else:
        kw["temperature"] = p.temperatura
        kw["extra_body"] = {"thinking": {"type": "disabled"}}
    if stream:
        kw["stream"] = True
        kw["stream_options"] = {"include_usage": True}
    return kw

