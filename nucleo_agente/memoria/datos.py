"""Datos duraderos del usuario (clave -> valor) y borrado total de su memoria."""
from __future__ import annotations

from nucleo_agente.memoria.cliente import _ahora
from nucleo_agente.memoria.constantes import TABLA_CHATS, TABLA_DATOS
from nucleo_agente.memoria.errores import ErrorMemoria


class _DatosMixin:
    def guardar_dato(self, clave: str, valor: str) -> None:
        """Crea o actualiza un dato duradero (ej. 'activos_seguidos' -> 'AAPL, EURUSD')."""
        clave = clave.strip().lower()
        if not clave or not valor.strip():
            raise ErrorMemoria("clave y valor no pueden estar vacíos.")
        self._ejecutar(
            self._db.table(TABLA_DATOS).upsert(
                {"usuario_id": self.usuario_id, "clave": clave, "valor": valor.strip(), "actualizada_en": _ahora()},
                on_conflict="usuario_id,clave",
            ),
            "guardar el dato",
        )

    def datos_usuario(self) -> dict[str, str]:
        filas = self._ejecutar(
            self._db.table(TABLA_DATOS).select("clave, valor").eq("usuario_id", self.usuario_id).order("clave"),
            "leer los datos del usuario",
        )
        return {f["clave"]: f["valor"] for f in filas}

    def borrar_dato(self, clave: str) -> None:
        self._ejecutar(
            self._db.table(TABLA_DATOS).delete().eq("usuario_id", self.usuario_id).eq("clave", clave.strip().lower()),
            "borrar el dato",
        )

    def olvidar_todo(self) -> None:
        """Borra TODA la memoria del usuario (conversaciones, mensajes y datos)."""
        self._ejecutar(self._db.table(TABLA_CHATS).delete().eq("usuario_id", self.usuario_id), "borrar las conversaciones")
        self._ejecutar(self._db.table(TABLA_DATOS).delete().eq("usuario_id", self.usuario_id), "borrar los datos")
        self.chat_id = None
        self._tiene_titulo = False
