"""CSS del rail y sus paneles: plantilla en estilos.css con las medidas (RAIL, PANEL, TOP) y los tooltips."""
import json
from pathlib import Path

from componentes_plataforma._estaticos import texto
from componentes_plataforma.riel.datos import BOTONES, PANEL, RAIL, TOP


def css() -> str:
    tips = "\n".join(
        f'    .st-key-rail_{pid} button::after {{ content: {json.dumps(nom)}; }}'
        for _, pid, nom in BOTONES
    )
    cuerpo = (texto(Path(__file__).parent / "estilos.css")
              .replace("__RAIL_PANEL_16__", str(RAIL + PANEL + 16)).replace("__RAIL_16__", str(RAIL + 16))
              .replace("__RAIL__", str(RAIL)).replace("__PANEL__", str(PANEL)).replace("__TOP__", str(TOP))
              .replace("__TIPS__", tips))
    return "\n<style>\n" + cuerpo + "</style>\n"
