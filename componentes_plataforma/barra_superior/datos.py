"""Íconos de línea (estilo Lucide/Feather, heredan color con currentColor) y emoji por tipo de notificación."""
from pathlib import Path

from componentes_plataforma._estaticos import datos_json

_D = datos_json(Path(__file__).parent / "iconos.json")

IC_BUSCAR = _D["buscar"]
IC_TEMA = _D["tema"]
IC_NOTIF = _D["notif"]
ICONO_TIPO = _D["tipo_notificacion"]
