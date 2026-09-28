"""
app.py
------
Dashboard interactivo de Piña & Jara - Financial Terminal,
diseñado con distribución de 3 columnas de forma limpia y modularizada.
"""
import os
import sys

# --- Arreglo de certificado SSL para rutas con tildes ---
# La ruta del proyecto contiene caracteres no ASCII ("análisis bursátiles"),
# lo que impide a curl_cffi (yfinance) leer el cacert.pem (error 77).
try:
    import certifi
    import shutil
    import tempfile
    _ca_ascii = os.path.join(tempfile.gettempdir(), "cacert_ascii.pem")
    shutil.copyfile(certifi.where(), _ca_ascii)
    os.environ["SSL_CERT_FILE"] = _ca_ascii
    os.environ["CURL_CA_BUNDLE"] = _ca_ascii
except Exception:
    pass
# --------------------------------------------------------

from types import ModuleType
from typing import Optional
import streamlit as st

# Asegurar ruta raíz
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Intentar importar la lógica principal del backend
main: Optional[ModuleType] = None
try:
    import main
except ImportError:
    pass

# Importar componentes modulares
from components.market_data import cargar_datos_mercado, actualizar_precios_mt5
from components.watchlist import renderizar_watchlist
from components.central_panel import renderizar_panel_central
from components.news_panel import renderizar_panel_noticias
from components.favoritos_bar import renderizar_barra_favoritos
from components.top_navbar import renderizar_barra_navegacion
from components.login import requerir_login

# Configuración inicial de la página
st.set_page_config(
    page_title="Dashboard agente analitico Piña & Jara",
    page_icon="📈",
    layout="wide"
)

# ==========================================
# ESTILOS CSS GLOBALES (tema oscuro tipo terminal de trading)
# ==========================================
st.markdown("""
    <style>
        /* Ocultar la barra propia de Streamlit (Deploy/Stop/⋮) — solo dejamos la nuestra */
        [data-testid="stHeader"] { display: none; }
        [data-testid="stToolbar"] { display: none; }
        /* Espacio arriba para que la barra fija no tape el contenido */
        .block-container { padding-top: 4.5rem; padding-bottom: 2rem; max-width: 100%; }

        /* Fondo y tipografía base */
        .stApp { background-color: #0b0f19; color: #e6edf3; }
        html, body, [class*="css"] { font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif; }

        /* Jerarquía de títulos discreta */
        h1 { font-size: 24px !important; font-weight: 700 !important; }
        h2 { font-size: 20px !important; font-weight: 700 !important; }
        h3 { font-size: 16px !important; font-weight: 700 !important; }
        p, span, label { font-size: 14px; }

        /* Botones oscuros y compactos */
        div.stButton > button {
            background-color: #161b22; color: #e6edf3; border: 1px solid #30363d;
            border-radius: 6px; font-size: 13px !important; padding: 4px 10px;
            min-height: 0; transition: all .15s ease;
        }
        div.stButton > button:hover { background-color: #21262d; border-color: #58a6ff; color: #ffffff; }

        /* Selectores oscuros */
        div[data-baseweb="select"] > div {
            background-color: #161b22 !important; border-color: #30363d !important;
        }
        .stSelectbox label, .stTextInput label, .stSlider label {
            font-size: 12px !important; color: #8b949e !important; font-weight: 600 !important;
        }

        /* Métricas */
        [data-testid="stMetricValue"] { font-size: 22px !important; }
        [data-testid="stMetricLabel"] { font-size: 13px !important; color: #8b949e !important; }

        /* Columnas más juntas */
        [data-testid="column"] { padding: 0 4px; }

        /* Entrada del chat */
        .stChatInput textarea { background-color: #161b22 !important; }

        /* Tarjetas con borde (favoritos y contenedores) en tema oscuro */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #161b22;
            border-radius: 8px;
        }

        /* Botón ✕ dentro de la tarjeta de favorito: minimalista (sin caja) */
        [class*="st-key-quitar_fav_"] button {
            background: transparent !important; border: none !important;
            color: #8b949e !important; padding: 0 !important;
            min-height: 0 !important; height: auto !important; font-size: 14px !important;
        }
        [class*="st-key-quitar_fav_"] button:hover { color: #f85149 !important; background: transparent !important; }

        /* Alinear "Seleccionar" y la estrella a la misma altura */
        [class*="st-key-btn_wl_real_"] button, [class*="st-key-btn_fav_"] button { height: 38px; }

        /* Barra de navegación FIJA arriba y a TODO EL ANCHO */
        .st-key-barra_nav_fija {
            position: fixed !important;
            top: 0; left: 0; right: 0;
            width: 100% !important;
            z-index: 100000;
            background: #0d1117;
            border-bottom: 1px solid #1b2430;
            padding: 10px 48px;  /* vertical simétrico para centrar el contenido */
            box-sizing: border-box;
        }
        .st-key-barra_nav_fija [data-testid="stVerticalBlock"] { gap: 0 !important; }
        .st-key-barra_nav_fija [data-testid="stVerticalBlockBorderWrapper"],
        .st-key-barra_nav_fija [data-testid="stVerticalBlock"] {
            background: transparent !important;
            border: none !important;
            border-radius: 0 !important;
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# LOGIN (Supabase): si no hay sesión, muestra el login y detiene la app.
# Si hay sesión, devuelve el usuario ({id, nombre, email}).
# ==========================================
usuario_actual = requerir_login()

# Overlay de carga a pantalla completa: SOLO en la primera carga (tras el login),
# para tapar el login mientras el dashboard se arma. En reruns posteriores (abrir
# el buscador, etc.) no aparece, así no parece que "refresca".
_primera_carga = not st.session_state.get("datos_cargados", False)
_overlay = st.empty()
if _primera_carga:
    _overlay.markdown("""
        <div style='position:fixed; inset:0; background:#0b0f19; z-index:99999;
                    display:flex; flex-direction:column; align-items:center;
                    justify-content:center; gap:14px; color:#8b949e;'>
            <div style='font-size:18px; font-weight:600;'>Cargando terminal…</div>
            <div style='font-size:13px;'>Conectando a MetaTrader 5</div>
        </div>
    """, unsafe_allow_html=True)

# Saldo total (equity) de la cuenta MT5 para mostrarlo en la barra superior
from tools.mt5_bridge import inicializar_mt5, obtener_info_cuenta
inicializar_mt5()
_info_cuenta = obtener_info_cuenta()
_saldo_mt5 = _info_cuenta.get("equity") if "error" not in _info_cuenta else None
_moneda_mt5 = _info_cuenta.get("currency", "USD") if "error" not in _info_cuenta else "USD"

# Barra de navegación superior (logo + buscador + usuario + saldo) — FIJA arriba
with st.container(key="barra_nav_fija"):
    renderizar_barra_navegacion(
        usuario=usuario_actual.get("nombre", "Usuario"),
        saldo=_saldo_mt5,
        moneda=_moneda_mt5,
    )

# Carga inicial de datos de mercado (estructura + primeros precios)
cargar_datos_mercado()

# ==========================================
# NÚMEROS EN VIVO (auto-refresco ligero cada 2 s)
# ==========================================
INTERVALO_PRECIOS = "2s"

# 1. Barra superior de FAVORITOS (precios en vivo)
@st.fragment(run_every=INTERVALO_PRECIOS)
def _favoritos_en_vivo():
    actualizar_precios_mt5()
    renderizar_barra_favoritos()

_favoritos_en_vivo()

# 2. Distribución principal de 3 columnas
col_left, col_center, col_right = st.columns([1, 2.1, 1.3])

with col_left:
    @st.fragment(run_every=INTERVALO_PRECIOS)
    def _watchlist_en_vivo():
        actualizar_precios_mt5()
        renderizar_watchlist()
    _watchlist_en_vivo()

with col_center:
    renderizar_panel_central(main)

# Panel ya visible: quitamos el overlay de carga (las noticias, más lentas por
# DeepSeek, se cargan después en su columna sin tapar nada).
_overlay.empty()

with col_right:
    renderizar_panel_noticias(main)
