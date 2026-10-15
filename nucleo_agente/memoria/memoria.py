"""Memoria persistente del agente: la clase se arma con la base y los mixins de conversaciones, datos y contexto."""
from __future__ import annotations

from nucleo_agente.memoria.base import _BaseMemoria
from nucleo_agente.memoria.contexto import _ContextoMixin
from nucleo_agente.memoria.conversaciones import _ConversacionesMixin
from nucleo_agente.memoria.datos import _DatosMixin


class Memoria(_ConversacionesMixin, _DatosMixin, _ContextoMixin, _BaseMemoria):
    """Memoria persistente de un usuario (Supabase). Ver el docstring del paquete."""
