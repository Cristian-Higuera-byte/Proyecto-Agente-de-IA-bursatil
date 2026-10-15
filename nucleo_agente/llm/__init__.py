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

Archivos: cliente.py (ClienteLLM), tipos.py, peticion.py, respuesta.py, argumentos.py y errores.py.
`python -m nucleo_agente.llm` sigue haciendo la prueba de conexión (ver __main__.py).
"""
from nucleo_agente.llm.argumentos import _parsear_argumentos  # noqa: F401
from nucleo_agente.llm.cliente import ClienteLLM
from nucleo_agente.llm.tipos import ErrorLLM, EventoStream, LlamadaHerramienta, RespuestaLLM
