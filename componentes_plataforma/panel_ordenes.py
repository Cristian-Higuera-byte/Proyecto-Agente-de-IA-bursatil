"""Paneles del agente (historial y órdenes propuestas). El código vive en componentes_plataforma/agente_paneles/ (historial,
propuestas, vigilancias, formato, estados JSON y estilos); este archivo se mantiene para que los imports de
aplicacion.py (inyectar_estilos_agente, renderizar_historial_agente, renderizar_ordenes_propuestas) y del chat
(cabecera_agente) sigan funcionando."""
from componentes_plataforma.agente_paneles import (cabecera_agente, inyectar_estilos_agente, renderizar_historial_agente,
                                       renderizar_ordenes_propuestas)

__all__ = ["inyectar_estilos_agente", "renderizar_historial_agente", "renderizar_ordenes_propuestas", "cabecera_agente"]
