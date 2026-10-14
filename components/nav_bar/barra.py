"""
nav_bar/barra.py
----------------
Barra lateral de navegación (estilo terminal). Colapsada = solo iconos (70 px);
expandida = iconos + texto (220 px). Expande/colapsa SIN reejecutar Python: los
botones se dibujan SIEMPRE solo con el ícono y el texto del modo expandido lo agrega
el CSS con ::after; un script (estatico/sidebar.js) intercepta el clic del ☰ y alterna
la clase `pj-sb-exp` en <html>, que el CSS anima. Al cargar la página parte retraída.

El CSS vive en estatico/sidebar.css con marcadores que `_css()` sustituye (selectores,
anchos y etiquetas por ítem); el JS del toggle en estatico/sidebar.js. Ambos se leen una
sola vez (lru_cache).
"""
import json
from functools import lru_cache
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

_ESTATICO = Path(__file__).resolve().parent / "estatico"

# (icono material, clave, etiqueta visible al expandir)
ITEMS = [
    (":material/home:", "home", "Inicio"),                       # panel de cuenta (estilo XM)
    (":material/candlestick_chart:", "trading", "Trading"),      # dashboard: gráfico + listas
    (":material/work:", "portafolio", "Cartera"),                # posiciones abiertas (bajo Trading)
    (":material/table_rows:", "cotizaciones", "Cotizaciones"),   # tablas estilo Investing
    (":material/content_copy:", "copytrading", "Copy trading"),  # estrategias (mock)
    (":material/newspaper:", "noticias", "Noticias"),
    (":material/dashboard:", "resumen", "Resumen"),           # dashboard del portafolio (F)
    (":material/menu_book:", "journal", "Diario"),            # trading journal (E)
]

# Anchos (px) de la barra lateral: colapsada / expandida.
ANCHO_COLAPSADO = 70
ANCHO_EXPANDIDO = 220
_ANIM = ".22s ease"
_COL = 'div[data-testid="stColumn"]:has(.pj-nav)'
_EXP = "html.pj-sb-exp"


@lru_cache(maxsize=None)
def _leer_estatico(nombre: str) -> str:
    """Lee un archivo de nav_bar/estatico/ (CSS/JS). Cacheado en memoria por proceso."""
    try:
        return (_ESTATICO / nombre).read_text(encoding="utf-8")
    except OSError:
        return ""


def _css() -> str:
    """CSS de la barra con los marcadores de estatico/sidebar.css sustituidos."""
    # Texto de cada botón en modo expandido (CSS ::after), generado desde ITEMS.
    etiquetas = "\n".join(
        f'    {_EXP} .st-key-nav_btn_{clave} button::after {{ content: {json.dumps(txt)}; }}'
        for _, clave, txt in ITEMS
    ) + f'\n    {_EXP} .st-key-nav_soporte button::after {{ content: "Soporte"; }}'

    css = (_leer_estatico("sidebar.css")
           .replace("__PAD_COL__", str(ANCHO_COLAPSADO + 20))
           .replace("__PAD_EXP__", str(ANCHO_EXPANDIDO + 20))
           .replace("__ANCHO_COL__", str(ANCHO_COLAPSADO))
           .replace("__ANCHO_EXP__", str(ANCHO_EXPANDIDO))
           .replace("__ANIM__", _ANIM)
           .replace("__ETIQUETAS__", etiquetas)
           .replace("__EXP__", _EXP)
           .replace("__COL__", _COL))
    return f"<style>\n{css}\n</style>"


def renderizar_barra_navegacion():
    if "nav_activo" not in st.session_state:
        st.session_state.nav_activo = "trading"  # al entrar, arranca en los gráficos

    st.markdown(_css() + '<div class="pj-nav"></div>', unsafe_allow_html=True)

    # Logo: "P&J" (gradiente) + "Piña & Jara" (solo expandida)
    st.markdown(
        "<div class='pj-logo'><span class='pj-logo-pj'>P&amp;J</span>"
        "<span class='pj-logo-txt'>Piña &amp; Jara</span></div>",
        unsafe_allow_html=True,
    )

    # Script que alterna la barra sin reejecutar Python (estatico/sidebar.js)
    with st.container(key="pj_sbjs"):
        components.html(f"<script>\n{_leer_estatico('sidebar.js')}\n</script>", height=0)

    # Botones SIEMPRE con solo el ícono (como la barra colapsada original);
    # el texto del modo expandido lo pone el CSS (::after).
    for icono, clave, etiqueta in ITEMS:
        activo = st.session_state.nav_activo == clave
        tipo = "primary" if activo else "secondary"
        if st.button(icono, key=f"nav_btn_{clave}", type=tipo):
            st.session_state.nav_activo = clave
            st.rerun()

    # Soporte: se empuja al fondo con margin-top:auto (ver CSS), sin espaciador fijo.
    if st.button(":material/headset_mic:", key="nav_soporte"):
        st.toast("Soporte técnico de Piña & Jara activo.")
