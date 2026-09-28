import html
import re

import streamlit as st
import MetaTrader5 as mt5  # type: ignore[import-untyped]
from typing import Any

try:
    from components.favoritos_bar import agregar_favorito, quitar_favorito
except ImportError:
    def agregar_favorito(ticker: str) -> Any:
        _ = ticker
        return None

    def quitar_favorito(ticker: str) -> Any:
        _ = ticker
        return None


# Altura (px) de la zona con scroll de la lista
ALTURA_LISTA = 640

# Icono circular por activo: (texto, fondo, color del texto)
_ICONOS = {
    "EURUSD": ("€", "linear-gradient(135deg,#3b82f6,#1e3a8a)", "#ffffff"),
    "GBPUSD": ("£", "linear-gradient(135deg,#ec4899,#831843)", "#ffffff"),
    "USDJPY": ("¥", "linear-gradient(135deg,#f87171,#991b1b)", "#ffffff"),
    "XAUUSD": ("Au", "linear-gradient(135deg,#fde047,#ca8a04)", "#1f1600"),
    "BTCUSD": ("₿", "linear-gradient(135deg,#fbbf24,#ea580c)", "#ffffff"),
    "ETHUSD": ("Ξ", "linear-gradient(135deg,#818cf8,#3730a3)", "#ffffff"),
    "US30": ("30", "linear-gradient(135deg,#38bdf8,#0c4a6e)", "#ffffff"),
}

_CSS = """
<style>
    /* Oculta el contenedor de este bloque de estilos (evita el hueco entre elementos) */
    div[data-testid="stElementContainer"]:has(.wl-css),
    div[data-testid="element-container"]:has(.wl-css) { display: none; }

    /* Panel general */
    .st-key-wl_panel {
        background: #0d1117;
        border: 1px solid #1f2937;
        border-radius: 10px;
        overflow: hidden;
    }
    .st-key-wl_panel,
    .st-key-wl_panel [data-testid="stVerticalBlock"],
    .st-key-wl_scroll { gap: 0 !important; }
    .st-key-wl_panel div[data-testid="stVerticalBlockBorderWrapper"] {
        background: transparent !important;
        border: none !important;
    }

    /* Encabezado */
    .wl-head { padding: 14px 16px 12px; border-bottom: 1px solid #1f2937; }
    .wl-title {
        display: flex; align-items: center; gap: 8px;
        font-size: 16px; font-weight: 700; color: #ffffff;
    }
    .wl-sub { font-size: 12px; color: #8b949e; margin-top: 2px; }

    /* Scrollbar discreto */
    .st-key-wl_scroll ::-webkit-scrollbar { width: 6px; }
    .st-key-wl_scroll ::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
    .st-key-wl_scroll ::-webkit-scrollbar-track { background: transparent; }

    /* Fila de activo */
    [class*="st-key-wlrow_"] {
        position: relative;
        overflow: hidden;
        transition: background 0.15s ease;
    }
    /* Streamlit añade margen inferior por defecto a cada widget; lo anulamos
       en todos los hijos de la fila para que el overlay de selección y el
       cálculo de alto de la fila coincidan exactamente con el visual (.wl-row) */
    [class*="st-key-wlrow_"] div[data-testid="stElementContainer"],
    [class*="st-key-wlrow_"] div[data-testid="element-container"] {
        margin: 0 !important;
    }
    .wl-row {
        display: flex; align-items: center; gap: 12px;
        padding: 11px 52px 11px 14px;
        border-bottom: 1px solid #1a2130;
        box-sizing: border-box;
    }
    /* El resaltado se pinta en el CONTENEDOR exterior de la fila (no en el
       div interno), para que ocupe exactamente el mismo rectángulo que el
       área clicable/hover -- así queda perfectamente centrado, sin quedar
       "subido" respecto al contenido visible. */
    [class*="st-key-wlrow_"]:hover { background: rgba(255,255,255,0.04); }
    [class*="st-key-wlrow_"]:has(.wl-row.sel) { background: #1a2236 !important; }

    .wl-ico {
        flex: 0 0 38px; width: 38px; height: 38px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 16px; font-weight: 800;
    }
    .wl-mid { flex: 1; min-width: 0; }
    .wl-tk { font-size: 16px; font-weight: 700; color: #ffffff; }
    .wl-nm {
        font-size: 13px; color: #8b949e; margin-top: 2px;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .wl-right { text-align: right; flex: 0 0 auto; }
    .wl-px {
        font-size: 16px; font-weight: 700; color: #ffffff;
        font-variant-numeric: tabular-nums;
    }
    .wl-var { font-size: 13px; font-weight: 600; margin-top: 2px; font-variant-numeric: tabular-nums; }

    /* Botón "Seleccionar": invisible, cubre toda la fila (la fila entera es clicable).
       Se fijan los 4 bordes explícitos (no el shorthand "inset") y se anulan
       margin/padding con !important para que el área clicable llegue de
       verdad de borde a borde, sin importar los defaults de Streamlit. */
    [class*="st-key-wlsel_"] {
        position: absolute !important;
        top: 0 !important; right: 0 !important; bottom: 0 !important; left: 0 !important;
        width: 100% !important; height: 100% !important;
        margin: 0 !important; padding: 0 !important;
        z-index: 1;
    }
    [class*="st-key-wlsel_"] * {
        width: 100% !important;
        height: 100% !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    [class*="st-key-wlsel_"] button {
        opacity: 0;
        cursor: pointer;
    }

    /* Botón de favorito: pequeño, a la derecha de la fila */
    [class*="st-key-wlfav_"] {
        position: absolute !important;
        right: 10px;
        top: 50%;
        transform: translateY(-50%);
        width: 32px !important;
        margin: 0 !important;
        z-index: 3;
    }
    [class*="st-key-wlfav_"] button {
        width: 32px !important;
        height: 32px !important;
        min-height: 32px !important;
        padding: 0 !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #586174 !important;
        border-radius: 8px !important;
    }
    [class*="st-key-wlfav_"] button p { font-size: 20px !important; line-height: 1 !important; }
    [class*="st-key-wlfav_"] button:hover {
        background: rgba(255,255,255,0.08) !important;
        color: #f5c518 !important;
    }
    /* Favorito activo (type="primary") */
    [class*="st-key-wlfav_"] button[kind="primary"],
    [class*="st-key-wlfav_"] [data-testid="stBaseButton-primary"] {
        color: #f5c518 !important;
    }

    /* Botón inferior */
    .st-key-wl_add { padding: 12px 14px 14px; }
    .st-key-wl_add button {
        background: transparent !important;
        border: 1px dashed #30363d !important;
        color: #8b949e !important;
        border-radius: 8px !important;
        min-height: 38px !important;
    }
    .st-key-wl_add button:hover {
        border-color: #58a6ff !important;
        color: #ffffff !important;
    }
</style>
<span class="wl-css"></span>
"""


def _icono_html(base: str) -> str:
    texto, fondo, color = _ICONOS.get(base, (base[:2], "#374151", "#ffffff"))
    return (
        f"<div class='wl-ico' style='background:{fondo}; color:{color};'>"
        f"{html.escape(texto)}</div>"
    )


def renderizar_watchlist():
    # Lista de activos oficiales extraídos directamente de MetaTrader 5 o respaldados en la sesión
    tickers_watchlist = ["EURUSD...", "GBPUSD...", "USDJPY...", "XAUUSD...", "BTCUSD", "ETHUSD", "US30"]

    # Asegurar que existan datos en session_state para estos símbolos
    info_activos_real = st.session_state.get("datos_mercado_real", {})

    st.markdown(_CSS, unsafe_allow_html=True)

    if "activo_seleccionado" not in st.session_state:
        st.session_state.activo_seleccionado = "EURUSD..."

    with st.container(key="wl_panel"):
        # Encabezado
        st.markdown(
            """
            <div class='wl-head'>
                <div class='wl-title'><span>🔥</span><span>LISTA DE ACTIVOS</span></div>
                <div class='wl-sub'>Precios de activos en tiempo real</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Contenedor con altura fija y scroll vertical individual
        with st.container(height=ALTURA_LISTA, border=False, key="wl_scroll"):
            for ticker in tickers_watchlist:
                item = info_activos_real.get(ticker, {
                    "nombre": ticker,
                    "precio": 1.0000,
                    "var": "+0.00 (0.00%)",
                    "sube": True
                })

                base = ticker.replace("...", "")
                slug = re.sub(r"\W", "", ticker)
                is_selected = (st.session_state.activo_seleccionado == ticker)
                color_var = "#2ebd85" if item.get("sube", True) else "#f6465d"

                precio_val = item.get('precio', 1.0)
                formato_precio = f"${precio_val:,.2f}" if precio_val > 100 else f"{precio_val:,.5f}"

                nombre = html.escape(str(item.get('nombre', ticker)))
                variacion = html.escape(str(item.get('var', '+0.00%')))
                clase_sel = " sel" if is_selected else ""

                es_favorito = ticker in st.session_state.get("favoritos", [])
                estrella = ":material/star:" if es_favorito else ":material/star_border:"
                ayuda = "Quitar de favoritos" if es_favorito else "Agregar a favoritos"

                with st.container(key=f"wlrow_{slug}"):
                    # Tarjeta visual del activo
                    st.markdown(f"""
                        <div class='wl-row{clase_sel}'>
                            {_icono_html(base)}
                            <div class='wl-mid'>
                                <div class='wl-tk'>{html.escape(base)}</div>
                                <div class='wl-nm'>{nombre}</div>
                            </div>
                            <div class='wl-right'>
                                <div class='wl-px'>{formato_precio}</div>
                                <div class='wl-var' style='color: {color_var};'>{variacion}</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    # Botón invisible que cubre toda la fila -> selecciona el activo.
                    # scope="app" fuerza una reejecución de TODA la app (no solo de
                    # este fragmento), que es lo que hace que components/central_panel.py
                    # -- que lee este mismo st.session_state.activo_seleccionado --
                    # cambie de inmediato el precio, el símbolo y el gráfico en vivo.
                    if st.button("Seleccionar", key=f"wlsel_{slug}"):
                        st.session_state.activo_seleccionado = ticker
                        st.toast(f"Mostrando {base} en el panel central.")
                        st.rerun(scope="app")

                    # Estrella de favoritos
                    if st.button(
                        estrella,
                        key=f"wlfav_{slug}",
                        help=ayuda,
                        type="primary" if es_favorito else "secondary",
                    ):
                        if es_favorito:
                            quitar_favorito(ticker)
                        else:
                            agregar_favorito(ticker)
                        st.rerun(scope="app")

        with st.container(key="wl_add"):
            if st.button("+ Add Holdings", use_container_width=True):
                st.toast("Función para agregar nuevos símbolos de MT5 próximamente.")