"""Rail de iconos de la derecha (Operar / DOM). El código vive en componentes_plataforma/riel/ (panel, estilos, botones y
script); este archivo se mantiene para que el import de aplicacion.py siga funcionando."""
from componentes_plataforma.riel import BOTONES, PANEL, RAIL, TOP, inyectar_css_rail, renderizar_rail_y_paneles

__all__ = ["RAIL", "PANEL", "TOP", "BOTONES", "inyectar_css_rail", "renderizar_rail_y_paneles"]
