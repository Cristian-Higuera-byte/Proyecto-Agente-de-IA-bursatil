"""Barra superior de activos favoritos del dashboard (estilo terminal de trading).

    estado.py    favoritos del usuario: cargar, agregar, quitar (se guardan en Supabase)
    tarjeta.py   HTML de cada tarjeta "burbuja" (ícono, precio en vivo, variación, flecha)
    barra.py     renderizar_barra_favoritos(): encabezado + 6 slots + botón «+»
    estilos.css  estilos de la barra
"""
from componentes_plataforma.favoritos.barra import renderizar_barra_favoritos
from componentes_plataforma.favoritos.estado import FAVORITOS_DEFAULT, FAVORITOS_MAX, agregar_favorito, quitar_favorito
from componentes_plataforma.favoritos.tarjeta import icono_activo

__all__ = ["renderizar_barra_favoritos", "agregar_favorito", "quitar_favorito", "icono_activo",
           "FAVORITOS_MAX", "FAVORITOS_DEFAULT"]
