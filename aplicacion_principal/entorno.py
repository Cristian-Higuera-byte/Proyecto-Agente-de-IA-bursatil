"""Preparación del entorno antes de importar el resto de la aplicación."""
import os
import traceback
from types import ModuleType
from typing import Optional


def corregir_certificado_ssl() -> None:
    """Arreglo de certificado SSL para rutas con tildes."""
    try:
        import certifi
        import shutil
        import tempfile
        _ca_ascii = os.path.join(tempfile.gettempdir(), "cacert_ascii.pem")
        if not os.path.exists(_ca_ascii):   # se copia una sola vez, no en cada rerun de Streamlit
            shutil.copyfile(certifi.where(), _ca_ascii)
        os.environ["SSL_CERT_FILE"] = _ca_ascii
        os.environ["CURL_CA_BUNDLE"] = _ca_ascii
    except Exception:
        pass


def importar_consola() -> Optional[ModuleType]:
    """Importa la lógica principal del backend (consola_agente.py) o devuelve None si no está disponible."""
    try:
        import consola_agente
        return consola_agente
    except ModuleNotFoundError as _e:
        if _e.name != "consola_agente":   # consola_agente.py existe pero le falta una dependencia: no se oculta
            traceback.print_exc()
    except Exception:           # cualquier otro fallo dentro de consola_agente.py
        traceback.print_exc()
    return None
