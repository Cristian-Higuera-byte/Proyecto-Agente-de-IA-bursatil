"""Núcleo del agente: conversación + bucle de herramientas.

No sabe nada de la interfaz (terminal, Streamlit...) ni de las herramientas
concretas. Emite eventos (EventoAgente) y quien lo use decide cómo mostrarlos.

Uso básico:
    agente = Agente()
    print(agente.responder("¿Qué día es hoy?"))

Uso con streaming (chat del dashboard):
    for ev in agente.responder_stream("..."):
        if ev.tipo == "texto": ...

Archivos: agente.py (clase Agente), ciclo.py (bucle de herramientas), eventos.py, prompt.py.
"""
from nucleo_agente.agente.agente import Agente
from nucleo_agente.agente.eventos import EventoAgente
from nucleo_agente.agente.instrucciones import PROMPT_RESPALDO, _prompt_sistema  # noqa: F401
from nucleo_agente.llm import ClienteLLM  # noqa: F401
from nucleo_agente.memoria import ErrorMemoria, Memoria  # noqa: F401
from herramientas_agente.base import REGISTRO, RegistroHerramientas  # noqa: F401
