"""
favoritos_bar.py
----------------
Barra superior de activos favoritos del dashboard.
El usuario agrega activos desde aquí (selector ➕) o desde la Lista de Activos
(botón +) y los quita con la ✕. Máximo 5, como en el diseño de referencia.
"""
import streamlit as st

FAVORITOS_MAX = 5
FAVORITOS_DEFAULT = ["BTCUSD", "ETHUSD", "XAUUSD...", "EURUSD...", "US30"]

# Íconos por activo: logos de cripto y banderas de divisas/índices (desde CDN)
_CRIPTO = {"BTCUSD": "btc", "ETHUSD": "eth", "LTCUSD": "ltc", "XRPUSD": "xrp"}
_BANDERAS = {
    "EURUSD": "eu", "GBPUSD": "gb", "USDJPY": "jp", "USDCHF": "ch",
    "AUDUSD": "au", "NZDUSD": "nz", "USDCAD": "ca", "US30": "us",
    "NAS100": "us", "SPX500": "us", "EURJPY": "eu", "EURGBP": "eu", "GBPJPY": "gb",
}


def icono_activo(ticker: str) -> str:
    """Devuelve el HTML de un ícono (logo cripto, bandera o emoji) para un activo."""
    base = ticker.replace("...", "").upper()
    if base in _CRIPTO:
        url = f"https://cdn.jsdelivr.net/npm/cryptocurrency-icons@0.18.1/svg/color/{_CRIPTO[base]}.svg"
        return f"<img src='{url}' width='20' height='20' style='vertical-align:middle;border-radius:50%;'>"
    if base in _BANDERAS:
        url = f"https://flagcdn.com/w40/{_BANDERAS[base]}.png"
        return f"<img src='{url}' width='22' style='vertical-align:middle;border-radius:3px;'>"
    if base.startswith("XAU"):
        return "<span style='font-size:18px;'>🥇</span>"
    if base.startswith("XAG"):
        return "<span style='font-size:18px;'>🥈</span>"
    return "<span style='font-size:16px;'>💱</span>"


def _init_favoritos():
    if "favoritos" not in st.session_state:
        st.session_state.favoritos = list(FAVORITOS_DEFAULT)


def agregar_favorito(ticker: str):
    """Agrega un activo a la barra de favoritos (respetando el máximo y sin duplicar)."""
    _init_favoritos()
    limpio = ticker.replace("...", "")
    if ticker in st.session_state.favoritos:
        st.toast(f"⭐ {limpio} ya está en tus favoritos")
        return
    if len(st.session_state.favoritos) >= FAVORITOS_MAX:
        st.toast(f"⚠️ Máximo {FAVORITOS_MAX} favoritos. Quita uno primero.")
        return
    st.session_state.favoritos.append(ticker)
    st.toast(f"⭐ {limpio} agregado a favoritos")


def quitar_favorito(ticker: str):
    _init_favoritos()
    if ticker in st.session_state.favoritos:
        st.session_state.favoritos.remove(ticker)


def renderizar_barra_favoritos():
    _init_favoritos()
    datos = st.session_state.get("datos_mercado_real", {})
    favs = st.session_state.favoritos
    disponibles = [t for t in datos.keys() if t not in favs]

    puede_agregar = len(favs) < FAVORITOS_MAX and bool(disponibles)
    total_cols = max(len(favs) + (1 if puede_agregar else 0), 1)
    cols = st.columns(total_cols)

    for i, tk in enumerate(favs):
        item = datos.get(tk, {"nombre": tk, "precio": 0.0, "var": "", "sube": True})
        sube = item.get("sube", True)
        color = "#3fb950" if sube else "#f85149"
        precio = item.get("precio", 0.0)
        precio_fmt = f"${precio:,.2f}" if precio > 100 else f"{precio:,.5f}"
        nombre = tk.replace("...", "")
        var = item.get("var", "")

        with cols[i]:
            with st.container(border=True):
                c_info, c_x = st.columns([4, 1], gap="small")
                with c_info:
                    st.markdown(
                        f"<div style='font-size:13px; font-weight:700; color:#ffffff;'>{nombre}</div>"
                        f"<div style='font-family:monospace; font-size:16px; font-weight:bold; color:#ffffff;'>{precio_fmt}</div>"
                        f"<div style='font-size:11px; font-weight:bold; color:{color};'>{var}</div>",
                        unsafe_allow_html=True,
                    )
                with c_x:
                    if st.button("✕", key=f"quitar_fav_{tk}", help=f"Quitar {nombre}"):
                        quitar_favorito(tk)
                        st.rerun()

    # Selector para agregar un nuevo favorito, dentro de la misma barra
    if puede_agregar:
        with cols[len(favs)]:
            st.markdown(
                """
                <div style='border:1px dashed #30363d; border-radius:8px; padding:8px 12px;
                            margin-bottom:2px; text-align:center; color:#8b949e; font-size:13px;'>
                    ➕ Agregar activo
                </div>
                """,
                unsafe_allow_html=True,
            )
            sel = st.selectbox(
                "Agregar activo",
                options=[""] + disponibles,
                format_func=lambda x: "Elegir…" if x == "" else x.replace("...", ""),
                label_visibility="collapsed",
            )
            if sel:
                agregar_favorito(sel)
                st.rerun()

    st.markdown("---")
