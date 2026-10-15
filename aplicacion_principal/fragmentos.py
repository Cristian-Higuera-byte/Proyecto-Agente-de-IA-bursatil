"""Fragmentos en vivo (números que se refrescan sin reejecutar toda la página).

Con servidor_datos.py corriendo, los precios/variaciones/saldo llegan por el feed SSE
(componentes_plataforma/flujo_vivo.py) y estos fragmentos solo hacen un refresco LENTO de
respaldo (sparkline, nombres, resincronía) → muchas menos reejecuciones y casi nada de
colisiones de deltas ("Cannot set a node at a delta path").
Sin el servidor, vuelven al refresco de 2 s de siempre.

Se crean en CADA ejecución del script (no al importar el módulo) porque `intervalo(...)`
depende de si el servidor está vivo en ese momento."""
from types import SimpleNamespace

import streamlit as st

from componentes_plataforma.datos_mercado import actualizar_precios_mt5
from componentes_plataforma.favoritos_barra import renderizar_barra_favoritos
from componentes_plataforma.flujo_vivo import intervalo
from componentes_plataforma.lista_activos_panel import renderizar_watchlist


def crear_fragmentos() -> SimpleNamespace:
    INTERVALO_PRECIOS = intervalo("2s")   # con feed: sin recarga periódica (evita el parpadeo)

    @st.fragment(run_every=INTERVALO_PRECIOS)
    def favoritos_en_vivo():
        actualizar_precios_mt5()
        renderizar_barra_favoritos()

    @st.fragment(run_every=INTERVALO_PRECIOS)
    def watchlist_en_vivo():
        renderizar_watchlist()   # precios ya los refresca favoritos_en_vivo

    def cartera_en_vivo():
        # Lista de posiciones abiertas (reemplaza al watchlist en la vista Cartera).
        # P/G total y por posición van por el feed; el refresco solo agrega/quita filas.
        # Se PAUSA el auto-refresco SOLO mientras se edita un nivel (ca_editando): así,
        # al escribir el TP/SL/distancia el rerun no quita el foco del input, pero con el
        # detalle abierto sin editar la lista sigue refrescando (detecta cierres solos).
        from componentes_plataforma.cartera_panel import renderizar_cartera_lista
        _cada = None if st.session_state.get("ca_editando") else intervalo("2s", "5s")
        st.fragment(run_every=_cada)(renderizar_cartera_lista)()

    return SimpleNamespace(favoritos=favoritos_en_vivo, watchlist=watchlist_en_vivo, cartera=cartera_en_vivo)
