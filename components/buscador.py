"""
buscador.py
-----------
Buscador de activos estilo XM: modal (st.dialog) con campo de búsqueda y filtro
por categoría. Lista LOS MISMOS activos que la lista de activos / watchlist
(st.session_state.datos_mercado_real). Al seleccionar uno, se carga en el gráfico
central (st.session_state.activo_seleccionado).
"""
import streamlit as st


def _activos_lista() -> list[dict]:
    """Activos de la watchlist: {name, desc, cat} desde datos_mercado_real."""
    datos = st.session_state.get("datos_mercado_real", {})
    salida: list[dict] = []
    for name, info in datos.items():
        salida.append({
            "name": name,                              # clave exacta (para el gráfico)
            "visible": name.replace("...", ""),        # nombre mostrado (sin sufijo)
            "desc": info.get("nombre", name),
            "cat": info.get("mercado", "Otros"),
        })
    salida.sort(key=lambda x: x["visible"])
    return salida


def _categorias(activos: list[dict]) -> list[str]:
    """Chips de categoría: 'Todo' + las categorías presentes en la lista."""
    cats = sorted({a["cat"] for a in activos})
    return ["Todo"] + cats


def _filtrar(activos: list[dict], q: str, cat: str) -> list[dict]:
    q = (q or "").strip().upper()
    res = []
    for a in activos:
        if cat and cat != "Todo" and a["cat"] != cat:
            continue
        if q and q not in a["visible"].upper() and q not in a["desc"].upper():
            continue
        res.append(a)
    return res


@st.dialog("Buscar activo", width="large")
def dialogo_buscador():
    activos = _activos_lista()
    if not activos:
        st.warning("La lista de activos aún no está cargada.")
        return

    q = st.text_input("Buscar", placeholder="Símbolo, ej. BTCUSD",
                      label_visibility="collapsed", key="buscar_q")
    cats = _categorias(activos)
    cat = st.segmented_control("Categoría", cats, default="Todo",
                               label_visibility="collapsed", key="buscar_cat")

    resultados = _filtrar(activos, q, cat or "Todo")
    st.caption(f"{len(resultados)} resultado(s)")

    with st.container(height=380):
        for a in resultados:
            c_info, c_add = st.columns([6, 1], vertical_alignment="center")
            with c_info:
                st.markdown(
                    f"**{a['visible']}** · <span style='color:#8b949e; font-size:11px;'>"
                    f"{a['cat'].upper()}</span><br>"
                    f"<span style='color:#8b949e; font-size:12px;'>{a['desc']}</span>",
                    unsafe_allow_html=True,
                )
            with c_add:
                if st.button("Abrir", key=f"pick_{a['name']}", width="stretch"):
                    st.session_state.activo_seleccionado = a["name"]
                    st.rerun()  # cierra el modal y recarga el gráfico con el activo