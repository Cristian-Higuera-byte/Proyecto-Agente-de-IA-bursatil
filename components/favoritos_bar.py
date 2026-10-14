"""Barra de FAVORITOS. El código vive en components/favoritos/ (estado, tarjeta, barra y estilos); este archivo
se mantiene para que los `from components.favoritos_bar import ...` de app.py, watchlist.py y mercados_panel.py
sigan funcionando."""
from components.favoritos import (FAVORITOS_DEFAULT, FAVORITOS_MAX, agregar_favorito, icono_activo,
                                  quitar_favorito, renderizar_barra_favoritos)

__all__ = ["renderizar_barra_favoritos", "agregar_favorito", "quitar_favorito", "icono_activo",
           "FAVORITOS_MAX", "FAVORITOS_DEFAULT"]
