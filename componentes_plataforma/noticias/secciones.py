# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ----------------------------------- INICIO Piña y Jara secciones .PY ----------------------------------
# -------------------------------------------------------------------------------------------------------

"""Secciones de la página de noticias: noticia principal, carrusel paginado y "Más noticias".

Cada noticia lleva un botón "abrir" invisible superpuesto (estilos.css) que guarda la noticia en
`st.session_state.noticia_abierta` para que `panel.py` abra su modal.
"""
import math

import streamlit as st

from componentes_plataforma.noticias.datos import MAX_CARRUSEL, POR_PAGINA
from componentes_plataforma.noticias.estilos import CSS_CARRUSEL
from componentes_plataforma.noticias.rss import cargar_mas_noticias, cargar_noticias
from componentes_plataforma.noticias.tarjetas import tarjeta_html


def renderizar_contenido():
    """Dibuja el contenido completo de la página de noticias.

    Carga las noticias (con caché); si no hay ninguna, muestra un aviso. Si hay, inyecta el CSS, pinta el
    título, la noticia principal, el carrusel paginado (4 por página, con flechas y vuelta al inicio) y
    llama a `renderizar_mas_noticias`. Usa `news_pag` de la sesión para recordar la página del carrusel.
    No devuelve nada; se ejecuta dentro de un fragmento con auto-refresco."""
    noticias = cargar_noticias()
    if not noticias:
        st.info("No se pudieron cargar las noticias en este momento. Reintenta en unos minutos.")
        return

    st.markdown(CSS_CARRUSEL, unsafe_allow_html=True)

    # Título de la sección (con línea superior, igual que "Más noticias")
    st.markdown(
        "<div style='border-top:1px solid #1f2937; padding-top:12px; margin:-22px 0 14px;'>"
        "<span style='font-size:24px; font-weight:800; color:#e6edf3;'>Noticias</span>"
        "<span style='color:#8b949e; font-size:13px; margin-left:8px;'>"
        "· Mercado de valores, Últimas noticias y Economía</span></div>",
        unsafe_allow_html=True,
    )

    # --- Noticia PRINCIPAL (clic -> modal) ---
    # La más reciente; se centra con columnas laterales vacías y se envuelve en un contenedor con key para el CSS
    hero = noticias[0]
    _, c_hero, _ = st.columns([0.6, 11, 0.6])
    with c_hero:
        with st.container(key="nhero"):
            st.html(f"""
                <div style="display:flex; gap:22px; align-items:flex-start; margin-bottom:22px; flex-wrap:wrap;">
                  <img src="{hero['img']}" referrerpolicy="no-referrer"
                       style="width:360px; height:220px; object-fit:cover; border-radius:10px;
                              flex:0 0 360px; background:#161b22;">
                  <div style="flex:1; min-width:280px;">
                    <h2 style="color:#ffffff; font-size:26px; font-weight:800; line-height:1.25; margin:0 0 12px;">{hero['title']}</h2>
                    <p style="color:#c9d1d9; font-size:15px; line-height:1.6; margin:0 0 10px;">
                       {hero['desc'][:320]}</p>
                    <span style="color:#586174; font-size:12px;">{hero['fecha']} &nbsp;·&nbsp; Ver noticia</span>
                  </div>
                </div>
            """)
            if st.button("abrir", key="nhero_btn"):
                st.session_state.noticia_abierta = hero
                st.rerun()

    # --- CARRUSEL paginado (4 por página, hasta 20, loop) ---
    # `pool` son las noticias del carrusel (sin la principal); `pag` la página actual con vuelta al inicio
    pool = noticias[1:1 + MAX_CARRUSEL]
    if not pool:
        return
    num_pag = max(1, math.ceil(len(pool) / POR_PAGINA))
    if "news_pag" not in st.session_state:
        st.session_state.news_pag = 0
    pag = st.session_state.news_pag % num_pag
    ventana = pool[pag * POR_PAGINA: pag * POR_PAGINA + POR_PAGINA]

    # Flecha izquierda, tarjetas y flecha derecha en una sola fila
    c_prev, c_cards, c_next = st.columns([0.6, 11, 0.6], vertical_alignment="center")

    with c_prev:
        if st.button("‹", key="news_prev"):
            st.session_state.news_pag = (pag - 1) % num_pag
            st.rerun(scope="fragment")

    with c_cards:
        cols = st.columns(POR_PAGINA)
        for pos, (col, n) in enumerate(zip(cols, ventana)):
            with col:
                with st.container(key=f"nc_{pos}"):
                    st.html(tarjeta_html(n))
                    if st.button("abrir", key=f"ncb_{pos}"):
                        st.session_state.noticia_abierta = n
                        st.rerun()

    with c_next:
        if st.button("›", key="news_next"):
            st.session_state.news_pag = (pag + 1) % num_pag
            st.rerun(scope="fragment")

    # --- Apartado "Más noticias" (RSS de Investing) ---
    renderizar_mas_noticias()


def renderizar_mas_noticias():
    """Dibuja el apartado "Más noticias" (Cripto, Forex y Economía) en una cuadrícula de 4 columnas.

    Muestra al inicio 8 noticias y un botón "Ver más noticias" que revela 8 más (estado `mas_mostrar` en la
    sesión); cuando ya se mostró todo aparece "Ver menos". No dibuja nada si no hay noticias. No devuelve
    nada."""
    todas = cargar_mas_noticias()
    if not todas:
        return

    st.markdown(
        "<div style='margin:30px 0 16px; border-top:1px solid #1f2937; padding-top:20px;'>"
        "<span style='font-size:22px; font-weight:800; color:#e6edf3;'>Más noticias</span>"
        "<span style='color:#8b949e; font-size:13px; margin-left:8px;'>· Cripto, Forex y Economía</span></div>",
        unsafe_allow_html=True,
    )

    # "Ver más" progresivo: empieza en 8 y revela de a 8.
    mostrar = st.session_state.get("mas_mostrar", 8)
    ns = todas[:mostrar]

    _, c_grid, _ = st.columns([0.6, 11, 0.6])
    with c_grid:
        # Filas de 4 tarjetas; cada una en un contenedor con key único (ync_N) para su botón invisible
        for fila in range(0, len(ns), 4):
            cols = st.columns(4)
            for k, (col, n) in enumerate(zip(cols, ns[fila:fila + 4])):
                with col:
                    with st.container(key=f"ync_{fila + k}"):
                        st.html(tarjeta_html(n))
                        if st.button("abrir", key=f"yncb_{fila + k}"):
                            st.session_state.noticia_abierta = n
                            st.rerun()

        # Botón Ver más / Ver menos (centrado)
        _, c_btn, _ = st.columns([1, 1.4, 1])
        with c_btn:
            if mostrar < len(todas):
                restantes = len(todas) - mostrar
                if st.button(f"Ver más noticias ({restantes})", key="mas_ver", width="stretch"):
                    st.session_state.mas_mostrar = mostrar + 8
                    st.rerun(scope="fragment")
            elif mostrar > 8:
                if st.button("Ver menos", key="mas_menos", width="stretch"):
                    st.session_state.mas_mostrar = 8
                    st.rerun(scope="fragment")


# -------------------------------------------------------------------------------------------------------
# ------------------------------------ FIN Piña y Jara secciones .PY ------------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
