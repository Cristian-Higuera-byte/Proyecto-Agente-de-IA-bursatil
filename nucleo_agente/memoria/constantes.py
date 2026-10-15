"""Tablas de Supabase y límites de la memoria."""

TABLA_CHATS = "agente_chats"
TABLA_MENSAJES = "agente_mensajes"
TABLA_DATOS = "agente_memoria_usuario"

MAX_TURNOS_CARGADOS = 6          # cuántos turnos recientes se reenvían al modelo al retomar un chat
MAX_RESUMENES_EN_CONTEXTO = 3    # cuántos resúmenes de chats anteriores se inyectan en el prompt
