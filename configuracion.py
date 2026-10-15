"""Configuración central del agente bursátil.

Todo lo que pueda cambiar (modelos, límites, rutas) vive aquí.
Las credenciales se leen del archivo .env (nunca se escriben en el código).

Variables esperadas en el .env:
    DEEPSEEK_API_KEY=sk-...
    DEEPSEEK_BASE_URL=https://api.deepseek.com   (opcional)
"""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent
load_dotenv(RAIZ / ".env")

# ──────────────────────────────────────────────────────────────
# DeepSeek
# ──────────────────────────────────────────────────────────────
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")


@dataclass(frozen=True)
class PerfilModelo:
    """Una forma de usar un modelo: qué modelo, con o sin razonamiento, y parámetros."""

    modelo: str
    thinking: bool                 # True = el modelo razona antes de responder
    esfuerzo: str = "high"         # low | high | max (solo aplica si thinking=True)
    temperatura: float = 0.3       # solo aplica si thinking=False
    max_tokens: int = 16384        # en modo thinking incluye los tokens de razonamiento


PERFILES: dict[str, PerfilModelo] = {
    # Respuestas cortas y consultas simples: más barato y rápido.
    "rapido": PerfilModelo("deepseek-flash", thinking=False, temperatura=0.3),
    # Perfil estándar del agente: razona y usa herramientas.
    "analisis": PerfilModelo("deepseek-flash", thinking=True, esfuerzo="high"),
    # Análisis más exigentes (informes, cruces de varias fuentes).
    "profundo": PerfilModelo("deepseek-v4-pro", thinking=True, esfuerzo="high"),
}
PERFIL_POR_DEFECTO = "analisis"

# ──────────────────────────────────────────────────────────────
# Comportamiento del agente
# ──────────────────────────────────────────────────────────────
MAX_ITERACIONES_HERRAMIENTAS = 8   # tope de ciclos "llamar herramienta → razonar" por consulta
TIMEOUT_LLM_SEG = 120
REINTENTOS_LLM = 3

# ──────────────────────────────────────────────────────────────
# Rutas
# ──────────────────────────────────────────────────────────────
DIR_DATOS = RAIZ / "data"
DIR_PROMPTS = RAIZ / "prompts"


def validar_config() -> None:
    """Falla temprano y con un mensaje claro si falta algo imprescindible."""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError(
            "Falta DEEPSEEK_API_KEY. Defínela en el archivo .env "
            f"(se busca en: {RAIZ / '.env'})."
        )