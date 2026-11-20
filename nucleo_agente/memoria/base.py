# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ------------------------------------- INICIO Piña y Jara base .PY -------------------------------------
# -------------------------------------------------------------------------------------------------------

"""Base de la clase Memoria: usuario, cliente de Supabase y utilidades internas.

Los mixins de conversaciones, datos y contexto se apoyan en lo que define _BaseMemoria.

Identidad (V19 de la auditoría): la memoria se ata a un id de usuario NUMÉRICO (el de la base de datos), nunca a un texto libre ni a una identidad fija. Solo el modo de un solo usuario
(sin CAPITAL_MULTIUSUARIO) acepta "local". Y antes de leer o escribir un chat se comprueba que ese chat pertenece al usuario de la memoria.
"""
from __future__ import annotations

from typing import Any

from nucleo_agente.memoria.cliente import _obtener_cliente
from nucleo_agente.memoria.constantes import TABLA_CHATS, TABLA_MENSAJES
from nucleo_agente.memoria.errores import ErrorMemoria
from herramientas.backends import sesiones_capital


# TITULO NORMALIZAR USUARIO

def normalizar_usuario(usuario_id: Any) -> str:
    """Id de usuario válido para la memoria: un entero positivo (como texto). "local" solo se acepta con el modo multiusuario apagado. Cualquier otro valor lanza ErrorMemoria."""
    texto = str(usuario_id if usuario_id is not None else "").strip()
    if texto.isascii() and texto.isdigit() and int(texto) > 0:
        return str(int(texto))
    if texto == "local" and not sesiones_capital.MULTIUSUARIO:
        return texto
    raise ErrorMemoria("Se necesita el id numérico de un usuario identificado para usar la memoria.")


# TITULO BASE MEMORIA

class _BaseMemoria:
    """Estado común de la memoria: usuario, chat activo y acceso perezoso al cliente de Supabase."""

    # TITULO INIT

    def __init__(self, usuario_id: str, cliente: Any = None) -> None:
        """Guarda el usuario (obligatorio, ErrorMemoria si está vacío) y opcionalmente un cliente ya creado.

        `cliente` permite inyectar un doble en pruebas; con None se crea al primer uso (ver `_db`).
        """
        self.usuario_id = normalizar_usuario(usuario_id)
        # Conversación activa (None hasta iniciar o retomar una) y si ya tiene título asignado.
        self.chat_id: str | None = None
        self._chat_verificado: str | None = None     # último chat cuyo dueño ya se comprobó
        self._tiene_titulo = False
        self._cli = cliente  # None = se crea al primer uso

    # ── Interno ───────────────────────────────────────────────

    # TITULO DB

    @property
    def _db(self) -> Any:
        """Cliente de Supabase de esta memoria; se crea al primer acceso."""
        if self._cli is None:
            self._cli = _obtener_cliente()
        return self._cli

    # TITULO EJECUTAR

    @staticmethod
    def _ejecutar(consulta: Any, accion: str) -> list[dict[str, Any]]:
        """Ejecuta una consulta de Supabase y devuelve sus filas ([] si no hay datos).

        `accion` describe la operación en infinitivo para el mensaje de error; cualquier excepción se
        convierte en ErrorMemoria.
        """
        try:
            return consulta.execute().data or []
        except Exception as e:  # noqa: BLE001
            raise ErrorMemoria(f"La base de datos falló al {accion}: {e}") from e

    # TITULO EXIGIR CHAT PROPIO

    def _exigir_chat_propio(self) -> None:
        """Comprueba que el chat activo pertenece a este usuario antes de leerlo o escribirlo; si no, lo suelta y lanza ErrorMemoria. Cada chat se verifica una sola vez."""
        if not self.chat_id or self.chat_id == self._chat_verificado:
            return
        filas = self._ejecutar(
            self._db.table(TABLA_CHATS).select("id").eq("id", self.chat_id).eq("usuario_id", self.usuario_id).limit(1),
            "comprobar la conversación",
        )
        if not filas:
            self.chat_id = None
            self._tiene_titulo = False
            raise ErrorMemoria("La conversación no pertenece a este usuario.")
        self._chat_verificado = self.chat_id

    # TITULO ULTIMO REGISTRO

    def _ultimo_registro(self) -> dict[str, Any] | None:
        """Devuelve el turno y orden del último mensaje del chat activo, o None si no tiene mensajes."""
        filas = self._ejecutar(
            self._db.table(TABLA_MENSAJES)
            .select("turno, orden")
            .eq("chat_id", self.chat_id)
            .order("orden", desc=True)
            .limit(1),
            "leer el último mensaje",
        )
        return filas[0] if filas else None

    # TITULO TITULO DESDE

    @staticmethod
    def _titulo_desde(mensajes: list[dict[str, Any]]) -> str | None:
        """Genera el título de un chat desde el primer mensaje del usuario (máx. 60 caracteres)."""
        for m in mensajes:
            if m.get("role") == "user" and m.get("content"):
                texto = " ".join(str(m["content"]).split())
                return texto[:60] + ("…" if len(texto) > 60 else "")
        return None


# -------------------------------------------------------------------------------------------------------
# --------------------------------------- FIN Piña y Jara base .PY --------------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
