"""Cliente de DeepSeek (API compatible con OpenAI): llamada completa y streaming."""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from openai import OpenAI

import configuracion  # type: ignore[import-not-found]
from nucleo_agente.llm.errores import traducir_error
from nucleo_agente.llm.peticion import construir_kwargs
from nucleo_agente.llm.respuesta import construir_respuesta
from nucleo_agente.llm.tipos import EventoStream, RespuestaLLM


class ClienteLLM:
    def __init__(self, perfil: str = configuracion.PERFIL_POR_DEFECTO):
        configuracion.validar_config()
        if perfil not in configuracion.PERFILES:
            raise ValueError(f"Perfil desconocido: {perfil!r}. Disponibles: {list(configuracion.PERFILES)}")
        self.perfil_por_defecto = perfil
        self._cliente = OpenAI(
            api_key=configuracion.DEEPSEEK_API_KEY,
            base_url=configuracion.DEEPSEEK_BASE_URL,
            timeout=configuracion.TIMEOUT_LLM_SEG,
            max_retries=configuracion.REINTENTOS_LLM,
        )

    # ── API pública ───────────────────────────────────────────

    def chat(
        self,
        mensajes: list[dict[str, Any]],
        herramientas: list[dict[str, Any]] | None = None,
        perfil: str | None = None,
    ) -> RespuestaLLM:
        """Una llamada completa (sin streaming)."""
        nombre = perfil or self.perfil_por_defecto
        try:
            r = self._cliente.chat.completions.create(
                **construir_kwargs(nombre, mensajes, herramientas, stream=False)
            )
        except Exception as e:
            raise traducir_error(e) from e

        msg = r.choices[0].message
        llamadas_raw = [
            {"id": tc.id, "nombre": tc.function.name, "args": tc.function.arguments or ""}
            for tc in (msg.tool_calls or [])
        ]
        return construir_respuesta(
            nombre,
            contenido=msg.content or "",
            razonamiento=getattr(msg, "reasoning_content", None),
            llamadas_raw=llamadas_raw,
            usage=r.usage,
        )

    def chat_stream(
        self,
        mensajes: list[dict[str, Any]],
        herramientas: list[dict[str, Any]] | None = None,
        perfil: str | None = None,
    ) -> Iterator[EventoStream]:
        """Igual que chat() pero emite eventos a medida que llegan.

        Pensado para el chat del dashboard: 'texto' se muestra en vivo y el
        último evento ('final') trae la respuesta completa con las llamadas
        a herramientas ya ensambladas.
        """
        nombre = perfil or self.perfil_por_defecto
        contenido: list[str] = []
        razon: list[str] = []
        llamadas: dict[int, dict[str, str]] = {}
        usage = None

        try:
            stream = self._cliente.chat.completions.create(
                **construir_kwargs(nombre, mensajes, herramientas, stream=True)
            )
            for chunk in stream:
                if getattr(chunk, "usage", None):
                    usage = chunk.usage
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta

                r = getattr(delta, "reasoning_content", None)
                if r:
                    razon.append(r)
                    yield EventoStream("razonamiento", r)

                if delta.content:
                    contenido.append(delta.content)
                    yield EventoStream("texto", delta.content)

                for tc in delta.tool_calls or []:
                    c = llamadas.setdefault(tc.index, {"id": "", "nombre": "", "args": ""})
                    if tc.id:
                        c["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            c["nombre"] = tc.function.name
                        if tc.function.arguments:
                            c["args"] += tc.function.arguments
        except Exception as e:
            raise traducir_error(e) from e

        respuesta = construir_respuesta(
            nombre,
            contenido="".join(contenido),
            razonamiento="".join(razon) if razon else None,
            llamadas_raw=[llamadas[i] for i in sorted(llamadas)],
            usage=usage,
        )
        yield EventoStream("final", respuesta=respuesta)

    # ── Internos ──────────────────────────────────────────────

    @staticmethod
    def _traducir_error(e: Exception):
        return traducir_error(e)
