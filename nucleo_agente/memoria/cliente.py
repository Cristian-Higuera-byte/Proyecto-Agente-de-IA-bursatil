"""Cliente de Supabase (se crea al primer uso, no al importar) y hora UTC."""
import os
from datetime import datetime, timezone
from typing import Any

import configuracion  # noqa: F401  (al importarlo se carga el .env)
from nucleo_agente.memoria.errores import ErrorMemoria

_cliente_global: Any = None


def _obtener_cliente() -> Any:
    global _cliente_global
    if _cliente_global is None:
        url = os.getenv("SUPABASE_URL", "")
        clave = os.getenv("SUPABASE_KEY", "")
        if not url or not clave:
            raise ErrorMemoria("Faltan SUPABASE_URL y/o SUPABASE_KEY en el .env.")
        try:
            from supabase import create_client

            _cliente_global = create_client(url, clave)
        except Exception as e:  # noqa: BLE001
            raise ErrorMemoria(f"No se pudo crear el cliente de Supabase: {e}") from e
    return _cliente_global


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()
