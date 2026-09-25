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
# Se apunta el certificado a una ruta ASCII ANTES de importar cualquier
# módulo que use yfinance (main y los componentes).
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
from components.market_data import cargar_datos_mercado
from components.top_bar import renderizar_barra_superior
from components.watchlist import renderizar_watchlist
from components.central_panel import renderizar_panel_central
from components.news_panel import renderizar_panel_noticias
from components.favoritos_bar import renderizar_barra_favoritos

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
        /* Barra superior de Streamlit visible (transparente para integrarse al tema) */
        [data-testid="stHeader"] { background: transparent; }
        .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 100%; }

        /* Fondo y tipografía base */
        .stApp { background-color: #0b0f19; color: #e6edf3; }
        html, body, [class*="css"] { font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif; }

        /* Jerarquía de títulos discreta (nada de 30px en todo) */
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
    </style>
""", unsafe_allow_html=True)

# 1. Cargar y actualizar datos seguros del mercado
cargar_datos_mercado()
# 2. Renderizar barra superior de FAVORITOS (activos elegidos por el usuario)
renderizar_barra_favoritos()
# 3. Distribución principal de 3 columnas
col_left, col_center, col_right = st.columns([1, 2.1, 1.3])
with col_left:
    renderizar_watchlist()
with col_center:
    renderizar_panel_central(main)
with col_right:
    renderizar_panel_noticias(main)
