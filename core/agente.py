"""Núcleo del agente: conversación + bucle de herramientas.

No sabe nada de la interfaz (terminal, Streamlit...) ni de las herramientas
concretas. Emite eventos (EventoAgente) y quien lo use decide cómo mostrarlos.

Uso básico:
    agente = Agente()
    print(agente.responder("¿Qué día es hoy?"))

Uso con streaming (chat del dashboard):
    for ev in agente.responder_stream("..."):
        if ev.tipo == "texto": ...
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterator

import config
import herramientas  # noqa: F401  (importarlo registra todas las herramientas)
from core.llm import ClienteLLM
from core.memoria import ErrorMemoria, Memoria
from herramientas.base import REGISTRO, RegistroHerramientas

PROMPT_RESPALDO = (
    "Eres un analista bursátil. Hoy es {fecha}. Usa las herramientas para obtener datos "
    "reales, no inventes cifras y responde siempre en español."
)


@dataclass
class EventoAgente:
    """tipo: 'razonamiento' | 'texto' | 'herramienta' | 'resultado' | 'fin'"""

    tipo: str
    texto: str = ""
    datos: dict[str, Any] = field(default_factory=dict)


def _prompt_sistema(contexto: str = "") -> str:
    ruta = config.DIR_PROMPTS / "sistema.md"
    base = ruta.read_text(encoding="utf-8") if ruta.exists() else PROMPT_RESPALDO
    # Solo la fecha (no la hora): así el prefijo del prompt no cambia durante el día
    # y DeepSeek puede reutilizar su caché de contexto (más barato y rápido).
    prompt = base.replace("{fecha}", datetime.now().astimezone().strftime("%Y-%m-%d"))
    return f"{prompt}\n\n{contexto}" if contexto else prompt


class Agente:
    def __init__(
        self,
        perfil: str | None = None,
        llm: ClienteLLM | None = None,
        registro: RegistroHerramientas = REGISTRO,
        usuario_id: str | None = None,   # None = sin memoria persistente
        continuar: bool = True,          # True = retoma la última conversación del usuario
    ) -> None:
        self.perfil = perfil                       # None = perfil por defecto de config.py
        self.llm = llm or ClienteLLM(perfil or config.PERFIL_POR_DEFECTO)
        self.registro = registro

        self.memoria: Memoria | None = None
        self._contexto = ""
        previo: list[dict[str, Any]] = []
        if usuario_id:
            try:
                self.memoria = Memoria(usuario_id)
                if continuar and self.memoria.retomar_ultimo_chat():
                    previo = self.memoria.cargar_historial()
                else:
                    self.memoria.iniciar_chat()
                self._contexto = self.memoria.contexto_previo()
            except ErrorMemoria as e:
                print(f"[Memoria] Desactivada en esta sesión: {e}")
                self.memoria = None
        self.historial: list[dict[str, Any]] = [{"role": "system", "content": self._prompt()}] + previo

    # ── API pública ───────────────────────────────────────────

    def reiniciar(self) -> None:
        """Empieza una conversación nueva. La anterior queda guardada en la memoria."""
        if self.memoria:
            try:
                self.memoria.iniciar_chat()
                self._contexto = self.memoria.contexto_previo()
            except ErrorMemoria as e:
                print(f"[Memoria] {e}")
        self.historial = [{"role": "system", "content": self._prompt()}]

    def _prompt(self) -> str:
        return _prompt_sistema(self._contexto)

    def _guardar_turno(self, desde: int) -> None:
        """Guarda el turno recién terminado. Si falla, el agente sigue sin memoria."""
        if not self.memoria:
            return
        try:
            self.memoria.guardar_turno(self.historial[desde:])
        except ErrorMemoria as e:
            print(f"[Memoria] No se pudo guardar el turno: {e}")

    def responder(self, texto: str) -> str:
        """Versión simple: devuelve solo la respuesta final."""
        final = ""
        for ev in self.responder_stream(texto):
            if ev.tipo == "fin":
                final = ev.texto
        return final

    def responder_stream(self, texto: str) -> Iterator[EventoAgente]:
        self.historial[0]["content"] = self._prompt()
        punto_inicio = len(self.historial)
        self.historial.append({"role": "user", "content": texto})

        completo = False
        try:
            for ev in self._ciclo():
                if ev.tipo == "fin":
                    completo = True
                    self._guardar_turno(punto_inicio)
                yield ev
        except BaseException:
            # Un turno a medias (error o cancelación) dejaría llamadas a herramientas
            # sin resultado en el historial y la API rechazaría el siguiente mensaje.
            if not completo:
                del self.historial[punto_inicio:]
            raise

    # ── Interno ───────────────────────────────────────────────

    def _ciclo(self) -> Iterator[EventoAgente]:
        esquemas = self.registro.esquemas() or None
        tokens = {"tokens_entrada": 0, "tokens_salida": 0}

        for _ in range(config.MAX_ITERACIONES_HERRAMIENTAS):
            final = None
            for ev in self.llm.chat_stream(self.historial, esquemas, self.perfil):
                if ev.tipo == "final":
                    final = ev.respuesta
                else:
                    yield EventoAgente(ev.tipo, ev.texto)

            if final is None:
                raise RuntimeError("El LLM no devolvió una respuesta final para este turno.")

            tokens["tokens_entrada"] += final.tokens_entrada
            tokens["tokens_salida"] += final.tokens_salida
            self.historial.append(final.mensaje)

            if not final.llamadas:
                yield EventoAgente("fin", final.contenido, {**tokens, "perfil": final.perfil})
                return

            for llamada in final.llamadas:
                yield EventoAgente("herramienta", llamada.nombre, llamada.argumentos)
                if llamada.error:
                    resultado = json.dumps({"error": llamada.error}, ensure_ascii=False)
                else:
                    resultado = self.registro.ejecutar(llamada.nombre, llamada.argumentos)
                self.historial.append(
                    {"role": "tool", "tool_call_id": llamada.id, "content": resultado}
                )
                yield EventoAgente("resultado", llamada.nombre, {"resultado": resultado})

        # Se alcanzó el tope de ciclos: se pide una respuesta final sin más herramientas.
        self.historial.append(
            {
                "role": "user",
                "content": (
                    "Alcanzaste el límite de consultas a herramientas. Responde ahora con la "
                    "información que ya tienes e indica qué te faltó."
                ),
            }
        )
        final = self.llm.chat(self.historial, None, self.perfil)
        tokens["tokens_entrada"] += final.tokens_entrada
        tokens["tokens_salida"] += final.tokens_salida
        self.historial.append(final.mensaje)
        yield EventoAgente("texto", final.contenido)
        yield EventoAgente("fin", final.contenido, {**tokens, "perfil": final.perfil})