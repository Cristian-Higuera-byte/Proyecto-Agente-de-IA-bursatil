"""Agente: conversación + memoria + bucle de herramientas (el bucle vive en ciclo.py)."""
from __future__ import annotations

from typing import Any, Iterator

import configuracion
import herramientas_agente  # noqa: F401  (importarlo registra todas las herramientas)
from nucleo_agente.agente.ciclo import _CicloMixin
from nucleo_agente.agente.eventos import EventoAgente
from nucleo_agente.agente.instrucciones import _prompt_sistema
from nucleo_agente.llm import ClienteLLM
from nucleo_agente.memoria import ErrorMemoria, Memoria
from herramientas_agente.base import REGISTRO, RegistroHerramientas


class Agente(_CicloMixin):
    def __init__(
        self,
        perfil: str | None = None,
        llm: ClienteLLM | None = None,
        registro: RegistroHerramientas = REGISTRO,
        usuario_id: str | None = None,   # None = sin memoria persistente
        continuar: bool = True,          # True = retoma la última conversación del usuario
    ) -> None:
        self.perfil = perfil                       # None = perfil por defecto de configuracion.py
        self.llm = llm or ClienteLLM(perfil or configuracion.PERFIL_POR_DEFECTO)
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
