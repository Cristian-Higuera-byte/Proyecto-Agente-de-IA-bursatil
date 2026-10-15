"""Construye la RespuestaLLM a partir de lo que llegó (contenido, razonamiento, llamadas y uso de tokens)."""
from __future__ import annotations

from typing import Any

import configuracion  # type: ignore[import-not-found]
from nucleo_agente.llm.argumentos import _parsear_argumentos
from nucleo_agente.llm.tipos import LlamadaHerramienta, RespuestaLLM


def construir_respuesta(
    nombre: str,
    contenido: str,
    razonamiento: str | None,
    llamadas_raw: list[dict[str, str]],
    usage: Any,
) -> RespuestaLLM:
    thinking = configuracion.PERFILES[nombre].thinking
    llamadas = []
    for c in llamadas_raw:
        args, error = _parsear_argumentos(c["args"])
        llamadas.append(
            LlamadaHerramienta(
                id=c["id"],
                nombre=c["nombre"],
                argumentos=args,
                argumentos_raw=c["args"] or "{}",
                error=error,
            )
        )
    return RespuestaLLM(
        contenido=contenido,
        # En thinking siempre se reenvía el campo (aunque venga vacío).
        razonamiento=(razonamiento or "") if thinking else None,
        llamadas=llamadas,
        tokens_entrada=getattr(usage, "prompt_tokens", 0) or 0,
        tokens_salida=getattr(usage, "completion_tokens", 0) or 0,
        perfil=nombre,
    )

