"""Núcleo del agente: LLM, bucle de herramientas y memoria.

Las importaciones son perezosas a propósito: así `python -m core.llm` (prueba
de conexión) no carga el agente ni las herramientas.

    from core import Agente, ClienteLLM
"""

__all__ = ["Agente", "ClienteLLM"]


def __getattr__(nombre: str):
    if nombre == "Agente":
        from .agente import Agente
        return Agente
    if nombre == "ClienteLLM":
        from .llm import ClienteLLM
        return ClienteLLM
    raise AttributeError(f"module 'core' has no attribute {nombre!r}")