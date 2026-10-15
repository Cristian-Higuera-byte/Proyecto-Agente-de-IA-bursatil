"""Base de la clase Memoria: usuario, cliente de Supabase y utilidades internas."""
from __future__ import annotations

from typing import Any

from nucleo_agente.memoria.cliente import _obtener_cliente
from nucleo_agente.memoria.constantes import TABLA_MENSAJES
from nucleo_agente.memoria.errores import ErrorMemoria


class _BaseMemoria:
    def __init__(self, usuario_id: str, cliente: Any = None) -> None:
        if not usuario_id or not str(usuario_id).strip():
            raise ErrorMemoria("Se necesita un usuario_id para usar la memoria.")
        self.usuario_id = str(usuario_id).strip()
        self.chat_id: str | None = None
        self._tiene_titulo = False
        self._cli = cliente  # None = se crea al primer uso

    # ── Interno ───────────────────────────────────────────────

    @property
    def _db(self) -> Any:
        if self._cli is None:
            self._cli = _obtener_cliente()
        return self._cli

    @staticmethod
    def _ejecutar(consulta: Any, accion: str) -> list[dict[str, Any]]:
        try:
            return consulta.execute().data or []
        except Exception as e:  # noqa: BLE001
            raise ErrorMemoria(f"Supabase falló al {accion}: {e}") from e

    def _ultimo_registro(self) -> dict[str, Any] | None:
        filas = self._ejecutar(
            self._db.table(TABLA_MENSAJES)
            .select("turno, orden")
            .eq("chat_id", self.chat_id)
            .order("orden", desc=True)
            .limit(1),
            "leer el último mensaje",
        )
        return filas[0] if filas else None

    @staticmethod
    def _titulo_desde(mensajes: list[dict[str, Any]]) -> str | None:
        for m in mensajes:
            if m.get("role") == "user" and m.get("content"):
                texto = " ".join(str(m["content"]).split())
                return texto[:60] + ("…" if len(texto) > 60 else "")
        return None
