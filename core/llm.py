"""Capa de acceso al LLM (DeepSeek, API compatible con OpenAI).

El resto del agente solo habla con ClienteLLM; si algún día se cambia de
proveedor o de modelo, este es el único archivo que se toca.

Puntos importantes de DeepSeek en modo thinking con herramientas:
  * `reasoning_content` de TODOS los turnos previos debe reenviarse en cada
    petición que lleve `tools`; si no, la API responde 400.
    `RespuestaLLM.mensaje` ya devuelve el mensaje del asistente listo para
    añadir al historial con ese campo incluido.
  * En thinking, `temperature` no tiene efecto, así que solo se envía en
    perfiles sin razonamiento.
"""
from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

import config  # type: ignore[import-not-found]


class ErrorLLM(Exception):
    """Error de la capa LLM con mensaje ya legible para el usuario."""


@dataclass
class LlamadaHerramienta:
    id: str
    nombre: str
    argumentos: dict[str, Any]
    argumentos_raw: str = "{}"
    error: str | None = None   # se rellena si el modelo envió un JSON inválido


@dataclass
class RespuestaLLM:
    contenido: str = ""
    razonamiento: str | None = None            # None = el perfil no usa thinking
    llamadas: list[LlamadaHerramienta] = field(default_factory=list)
    tokens_entrada: int = 0
    tokens_salida: int = 0
    perfil: str = ""

    @property
    def mensaje(self) -> dict[str, Any]:
        """Mensaje del asistente listo para añadir al historial."""
        msg: dict[str, Any] = {"role": "assistant", "content": self.contenido}
        if self.razonamiento is not None:
            msg["reasoning_content"] = self.razonamiento
        if self.llamadas:
            msg["tool_calls"] = [
                {
                    "id": c.id,
                    "type": "function",
                    "function": {"name": c.nombre, "arguments": c.argumentos_raw or "{}"},
                }
                for c in self.llamadas
            ]
        return msg


@dataclass
class EventoStream:
    """tipo: 'razonamiento' | 'texto' | 'final' (en 'final' viene la RespuestaLLM completa)."""

    tipo: str
    texto: str = ""
    respuesta: RespuestaLLM | None = None


def _parsear_argumentos(raw: str) -> tuple[dict[str, Any], str | None]:
    if not raw:
        return {}, None
    try:
        datos = json.loads(raw)
        if not isinstance(datos, dict):
            return {}, f"Los argumentos deben ser un objeto JSON, llegó: {raw!r}"
        return datos, None
    except json.JSONDecodeError:
        return {}, f"Argumentos con JSON inválido: {raw!r}"


class ClienteLLM:
    def __init__(self, perfil: str = config.PERFIL_POR_DEFECTO):
        config.validar_config()
        if perfil not in config.PERFILES:
            raise ValueError(f"Perfil desconocido: {perfil!r}. Disponibles: {list(config.PERFILES)}")
        self.perfil_por_defecto = perfil
        self._cliente = OpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
            timeout=config.TIMEOUT_LLM_SEG,
            max_retries=config.REINTENTOS_LLM,
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
                **self._kwargs(nombre, mensajes, herramientas, stream=False)
            )
        except Exception as e:
            raise self._traducir_error(e) from e

        msg = r.choices[0].message
        llamadas_raw = [
            {"id": tc.id, "nombre": tc.function.name, "args": tc.function.arguments or ""}
            for tc in (msg.tool_calls or [])
        ]
        return self._construir(
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
                **self._kwargs(nombre, mensajes, herramientas, stream=True)
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
            raise self._traducir_error(e) from e

        respuesta = self._construir(
            nombre,
            contenido="".join(contenido),
            razonamiento="".join(razon) if razon else None,
            llamadas_raw=[llamadas[i] for i in sorted(llamadas)],
            usage=usage,
        )
        yield EventoStream("final", respuesta=respuesta)

    # ── Internos ──────────────────────────────────────────────

    def _kwargs(
        self,
        nombre: str,
        mensajes: list[dict[str, Any]],
        herramientas: list[dict[str, Any]] | None,
        stream: bool,
    ) -> dict[str, Any]:
        p = config.PERFILES[nombre]
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

    def _construir(
        self,
        nombre: str,
        contenido: str,
        razonamiento: str | None,
        llamadas_raw: list[dict[str, str]],
        usage: Any,
    ) -> RespuestaLLM:
        thinking = config.PERFILES[nombre].thinking
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

    @staticmethod
    def _traducir_error(e: Exception) -> ErrorLLM:
        if isinstance(e, ErrorLLM):
            return e
        if isinstance(e, APIStatusError):
            codigo = e.status_code
            if codigo == 401:
                return ErrorLLM("DeepSeek rechazó la API key (401). Revisa DEEPSEEK_API_KEY en el .env.")
            if codigo == 402:
                return ErrorLLM("Saldo insuficiente en la cuenta de DeepSeek (402).")
            if codigo == 429:
                return ErrorLLM("Límite de peticiones de DeepSeek alcanzado (429). Intenta de nuevo en un momento.")
            return ErrorLLM(f"Error de la API de DeepSeek ({codigo}): {e.message}")
        if isinstance(e, APITimeoutError):
            return ErrorLLM("DeepSeek tardó demasiado en responder (timeout).")
        if isinstance(e, APIConnectionError):
            return ErrorLLM("No se pudo conectar con DeepSeek. Revisa tu conexión a internet.")
        return ErrorLLM(f"Error inesperado en la capa LLM: {e}")


if __name__ == "__main__":
    # Prueba rápida de conexión:  python -m core.llm   (desde la carpeta agente_bursatil)
    llm = ClienteLLM("rapido")
    for ev in llm.chat_stream([{"role": "user", "content": "Responde solo: conexión OK"}]):
        if ev.tipo == "texto":
            print(ev.texto, end="", flush=True)
        elif ev.tipo == "final" and (respuesta := ev.respuesta) is not None:
            print(f"\n[{respuesta.tokens_entrada} tokens entrada / {respuesta.tokens_salida} salida]")