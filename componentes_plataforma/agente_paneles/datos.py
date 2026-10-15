"""Estados de una orden del agente -> (texto, color), en estados.json, y la clave del aviso en sesión."""
from pathlib import Path

from componentes_plataforma._estaticos import datos_json

CLAVE_AVISO = "_aviso_orden"   # session_state: aviso (ok|error, mensaje) tras confirmar/rechazar/autorizar

ESTADOS = {k: tuple(v) for k, v in datos_json(Path(__file__).parent / "estados.json").items()}
