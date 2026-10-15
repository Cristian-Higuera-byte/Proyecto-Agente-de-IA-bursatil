"""Bucle de herramientas del agente: el modelo responde, pide herramientas, se ejecutan y se repite."""
from __future__ import annotations

import json
from typing import Iterator

import configuracion
from nucleo_agente.agente.eventos import EventoAgente


class _CicloMixin:
    def _ciclo(self) -> Iterator[EventoAgente]:
        esquemas = self.registro.esquemas() or None
        tokens = {"tokens_entrada": 0, "tokens_salida": 0}

        for _ in range(configuracion.MAX_ITERACIONES_HERRAMIENTAS):
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
