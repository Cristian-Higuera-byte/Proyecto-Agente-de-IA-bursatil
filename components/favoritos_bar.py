"""
favoritos_bar.py
----------------
Barra superior de activos favoritos del dashboard, estilo terminal de trading
(mockup): panel con encabezado "Mis Favoritos" + contador, paginación con
flechas, "Ver todos" y un engranaje para gestionar. Cada tarjeta es una "burbuja"
con contorno degradé verde (sube) / rojo (baja): ícono, nombre, precio en vivo,
variación y una flecha de tendencia.

Los favoritos se guardan por usuario en Supabase (columna `favorito` de
watchlist_usuario, vía tools/watchlist_manager).
"""
import re

import streamlit as st

from components.live_feed import attrs as _live
from components.iconos import icono_activo as _icono
from tools import watchlist_manager as wl

FAVORITOS_MAX = 6       # tope de favoritos por usuario (solo caben 6 en una fila)
_VISIBLES = 6           # tarjetas visibles

FAVORITOS_DEFAULT = wl.FAVORITOS_DEFAULT


_CSS = """
<style>
  .st-key-fav_panel {
    background:#0d1117; border:1px solid #1f2630; border-radius:14px;
    padding:8px 16px 10px; margin-bottom:10px;
  }
  /* Menos espacio entre el encabezado y las tarjetas */
  .st-key-fav_panel [data-testid="stVerticalBlock"] { gap:.3rem !important; }
  .st-key-fav_panel [data-testid="stHorizontalBlock"] { gap:10px !important; }
  .fav-head { display:flex; align-items:center; gap:10px; margin:0 0 2px; }
  .fav-chip { width:28px; height:28px; border-radius:9px; flex:0 0 auto;
              display:flex; align-items:center; justify-content:center;
              background:linear-gradient(135deg, rgba(240,180,41,.20), rgba(255,143,0,.14));
              border:1px solid #2c2616; }
  .fav-mi { font-family:'Material Symbols Rounded'; font-weight:400; font-size:17px; line-height:1;
            background:linear-gradient(135deg,#ffd454,#f0a91e);
            -webkit-background-clip:text; background-clip:text; color:transparent; }
  .fav-title { color:#e6edf3; font-weight:800; font-size:14.5px; letter-spacing:.2px; }
  .fav-badge { background:#1a2130; color:#aeb7c2; font-size:10.5px; font-weight:700;
               padding:2px 9px; border-radius:999px; line-height:1.4; }
  /* Tarjeta tipo burbuja con contorno degradé verde (sube) / rojo (baja).
     Técnica de borde con degradado: dos fondos (padding-box = relleno,
     border-box = el degradado) + borde transparente. */
  .fav-card { width:100%; box-sizing:border-box; display:flex; align-items:center; gap:11px;
              border:1.5px solid transparent; border-radius:16px; padding:9px 14px;
              background:linear-gradient(#0f1620,#0f1620) padding-box,
                         linear-gradient(135deg,#2a3340,#2a3340) border-box;
              transition:transform .14s ease, box-shadow .14s ease; }
  .fav-card.up   { background:linear-gradient(#0e1620,#0e1620) padding-box,
                             linear-gradient(135deg,#3fb950,#14532d) border-box; }
  .fav-card.down { background:linear-gradient(#141015,#141015) padding-box,
                             linear-gradient(135deg,#f85149,#7f1d1d) border-box; }
  .fav-card:hover { transform:translateY(-1px); box-shadow:0 7px 20px rgba(0,0,0,.38); }
  .fav-ic { display:inline-flex; align-items:center; flex:0 0 auto; }
  .fav-l { display:flex; flex-direction:column; gap:1px; min-width:0; flex:1 1 auto; }
  .fav-tk { color:#e6edf3; font-weight:700; font-size:12.5px; white-space:nowrap;
            overflow:hidden; text-overflow:ellipsis; }
  .fav-row { display:flex; align-items:baseline; gap:8px; min-width:0; }
  .fav-px { color:#ffffff; font-weight:800; font-size:15px; line-height:1.15;
            font-variant-numeric:tabular-nums; white-space:nowrap; }
  .fav-var { font-size:11px; font-weight:700; white-space:nowrap; font-variant-numeric:tabular-nums;
             overflow:hidden; text-overflow:ellipsis; }
  .fav-arrow { flex:0 0 auto; font-size:16px; font-weight:800; line-height:1; align-self:center; }
  .fav-empty { color:#6e7681; font-size:13px; padding:14px 2px; }

  /* Cada slot es contenedor relativo para posicionar la ✕ sobre la tarjeta */
  [class*="st-key-favslot_"] { position:relative; }

  /* Tarjeta del activo que está en el gráfico: anillo sutil + sombra (mantiene
     el contorno degradé verde/rojo; solo agrega un halo para marcarla). */
  .fav-card.sel { box-shadow:0 0 0 1px rgba(255,255,255,.22), 0 6px 18px rgba(0,0,0,.4); }

  /* Botón invisible que cubre TODA la tarjeta -> selecciona el activo
     (mismo patrón que wlsel_ en watchlist.py). Queda bajo la ✕ (z-index 6). */
  [class*="st-key-favsel_"] {
    position:absolute !important; inset:0 !important;
    width:100% !important; height:100% !important;
    margin:0 !important; padding:0 !important; z-index:1;
  }
  [class*="st-key-favsel_"] * {
    width:100% !important; height:100% !important; min-height:0 !important;
    margin:0 !important; padding:0 !important;
  }
  [class*="st-key-favsel_"] button { opacity:0; cursor:pointer; }
  [class*="st-key-favx_"] { position:absolute !important; top:3px; right:3px;
                            z-index:6; width:auto !important; min-width:0 !important; }
  [class*="st-key-favx_"] button {
    background:transparent !important; border:none !important; box-shadow:none !important;
    color:#5c636e !important; padding:0 5px !important; min-height:0 !important;
    height:20px !important; line-height:1 !important; font-size:13px !important;
  }
  [class*="st-key-favx_"] button:hover {
    color:#f85149 !important; background:transparent !important; border:none !important;
  }
  /* Botón "+" en el espacio libre: tarjeta punteada del mismo alto */
  [class*="st-key-favadd"] button {
    width:100% !important; min-height:60px !important; background:transparent !important;
    border:1.5px dashed #2f3d4f !important; color:#8b949e !important; border-radius:16px !important;
    font-size:20px !important;
  }
  [class*="st-key-favadd"] button:hover { border-color:#3fb950 !important; color:#e6edf3 !important; }
</style>
"""


def icono_activo(ticker: str, size: int = 30) -> str:
    """Ícono del activo (estilo XM). Lo define components/iconos.py para todo el
    dashboard; se mantiene aquí por compatibilidad con quien lo importa."""
    return _icono(ticker, size)


def _fmt_precio(precio: float) -> str:
    if precio >= 100:
        return f"{precio:,.2f}"
    return f"{precio:,.5f}"


def _uid():
    usuario = st.session_state.get("usuario_info") or {}
    return usuario.get("id") if isinstance(usuario, dict) else None


def _init_favoritos():
    """Carga los favoritos del usuario desde Supabase (una vez por sesión)."""
    if "favoritos" not in st.session_state:
        favs = wl.obtener_favoritos(_uid())
        st.session_state.favoritos = favs if favs else list(FAVORITOS_DEFAULT)


def agregar_favorito(ticker: str):
    """Agrega un activo a favoritos (respetando el máximo y sin duplicar)."""
    _init_favoritos()
    limpio = ticker.replace("...", "")
    if ticker in st.session_state.favoritos:
        st.toast(f"⭐ {limpio} ya está en tus favoritos")
        return
    if len(st.session_state.favoritos) >= FAVORITOS_MAX:
        st.toast(f"⚠️ Máximo {FAVORITOS_MAX} favoritos. Quita uno primero.")
        return
    st.session_state.favoritos.append(ticker)
    wl.marcar_favorito(_uid(), ticker, True)
    st.toast(f"⭐ {limpio} agregado a favoritos")


def quitar_favorito(ticker: str):
    _init_favoritos()
    if ticker in st.session_state.favoritos:
        st.session_state.favoritos.remove(ticker)
        wl.marcar_favorito(_uid(), ticker, False)


def _tarjeta_html(tk: str, datos: dict) -> str:
    item = datos.get(tk, {"precio": 0.0, "var": "", "sube": True})
    sube = item.get("sube", True)
    dir_cls = "up" if sube else "down"
    color = "#3fb950" if sube else "#f85149"
    flecha = "↗" if sube else "↘"
    precio = item.get("precio", 0.0)
    var = item.get("var", "") or "0.00 (0.00%)"
    nombre = tk.replace("...", "")
    sel = " sel" if st.session_state.get("activo_seleccionado") == tk else ""
    return (
        f"<div class='fav-card {dir_cls}{sel}'>"
        f"<span class='fav-ic'>{icono_activo(tk)}</span>"
        "<div class='fav-l'>"
        f"<div class='fav-tk'>{nombre}</div>"
        "<div class='fav-row'>"
        f"<span class='fav-px' {_live(tk, 'px')}>{_fmt_precio(precio)}</span>"
        f"<span class='fav-var' {_live(tk, 'var')} style='color:{color};'>{var}</span>"
        "</div></div>"
        f"<span class='fav-arrow' style='color:{color};'>{flecha}</span>"
        "</div>"
    )


def _slot_agregar(disponibles):
    """Tarjeta '+' en el hueco libre: popover con selector para agregar favorito."""
    with st.container(key="favadd"):
        with st.popover("＋", help="Agregar favorito", use_container_width=True):
            sel = st.selectbox(
                "Agregar activo", options=[""] + disponibles,
                format_func=lambda x: "Elegir activo…" if x == "" else x.replace("...", ""),
                label_visibility="collapsed", key="fav_add_sel",
            )
            if sel:
                agregar_favorito(sel)
                st.rerun(scope="fragment")


def renderizar_barra_favoritos():
    _init_favoritos()
    datos = st.session_state.get("datos_mercado_real", {})
    favs = list(st.session_state.favoritos)
    lista = st.session_state.get("watchlist_simbolos") or list(datos.keys())
    disponibles = [t for t in lista if t not in favs]
    total = len(favs)
    puede_agregar = bool(disponibles) and total < FAVORITOS_MAX

    with st.container(key="fav_panel"):
        st.html(_CSS)

        # --- Encabezado: solo título + contador ---
        st.html(
            "<div class='fav-head'>"
            "<span class='fav-chip'><span class='fav-mi'>star</span></span>"
            "<span class='fav-title'>Mis favoritos</span>"
            f"<span class='fav-badge'>{total}</span></div>"
        )

        # --- 6 slots: favorito (con ✕), '+' en el primer hueco libre, o vacío ---
        cols = st.columns(_VISIBLES, gap="small")
        for i in range(_VISIBLES):
            with cols[i]:
                with st.container(key=f"favslot_{i}"):
                    if i < total:
                        tk = favs[i]
                        st.html(_tarjeta_html(tk, datos))
                        # Clic en la tarjeta -> carga el activo en el gráfico, el
                        # ticket y la cabecera (igual que la watchlist). scope="app"
                        # porque esos paneles están fuera de este fragmento. Sin
                        # st.toast antes del rerun (error "Cannot set a node at a
                        # delta path", ver watchlist.py).
                        slug = re.sub(r"\W", "", tk)
                        if st.button("Seleccionar", key=f"favsel_{slug}"):
                            st.session_state.activo_seleccionado = tk
                            st.rerun(scope="app")
                        if st.button("✕", key=f"favx_{tk}", help="Quitar de favoritos"):
                            quitar_favorito(tk)
                            st.rerun(scope="fragment")
                    elif i == total and puede_agregar:
                        _slot_agregar(disponibles)
                    else:
                        st.html("<div class='fav-card' style='visibility:hidden;'></div>")
