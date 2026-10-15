"""Prueba rápida de conexión:  python -m nucleo_agente.llm   (desde la carpeta del proyecto)."""
from nucleo_agente.llm import ClienteLLM

llm = ClienteLLM("rapido")
for ev in llm.chat_stream([{"role": "user", "content": "Responde solo: conexión OK"}]):
    if ev.tipo == "texto":
        print(ev.texto, end="", flush=True)
    elif ev.tipo == "final" and (respuesta := ev.respuesta) is not None:
        print(f"\n[{respuesta.tokens_entrada} tokens entrada / {respuesta.tokens_salida} salida]")