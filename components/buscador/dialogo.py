"""
buscador/dialogo.py
-------------------
Modal (st.dialog) del buscador de activos, estilo XM: campo de texto + filtro por
categoría + lista con revelado progresivo ("Ver más"). Cada resultado se puede "Abrir"
(cargar en el gráfico) o "➕ Agregar" a la watchlist. Se abre con el patrón bandera +
render en app.py (`abrir_buscador` marca, `render_buscador` dibuja) para que el diálogo
no choque con los fragmentos de auto-refresco y deje la pantalla en blanco.
"""
import streamlit as st

from .datos import cargar_simbolos_broker, categorias, filtrar, _agregar_a_watchlist

_PASO_RESULTADOS = 40  # cuántos se revelan al inicio y por cada "Ver más"


def abrir_buscador():
    """Marca que el diálogo debe mostrarse (se renderiza en app.py con
    `render_buscador`). Este patrón (bandera + render en el script principal)
    evita que el diálogo choque con los fragmentos de auto-refresco y deje la
    pantalla en blanco al interactuar dentro."""
    st.session_state.mostrar_buscador = True


def _cerrar_buscador():
    st.session_state.mostrar_buscador = False


def render_buscador():
    """Llamar UNA vez al final de app.py: abre el diálogo si la bandera está activa."""
    if st.session_state.get("mostrar_buscador"):
        _dialogo_buscador()


@st.dialog("Buscar activo", width="large", on_dismiss=_cerrar_buscador)
def _dialogo_buscador():
    activos = cargar_simbolos_broker()
    if not activos:
        st.warning("No se pudieron cargar los símbolos de MT5. ¿Está abierto el terminal?")
        return

    q = st.text_input("Buscar", placeholder="Símbolo o nombre, ej. AAPL, EUR, Bitcoin…",
                      label_visibility="collapsed", key="buscar_q")
    cat = st.segmented_control("Categoría", categorias(activos), default="Todo",
                               label_visibility="collapsed", key="buscar_cat")

    resultados = filtrar(activos, q, cat or "Todo")

    # Revelado progresivo: se reinicia al cambiar la búsqueda o la categoría.
    filtro_actual = (q.strip().upper(), cat or "Todo")
    if st.session_state.get("_buscar_filtro") != filtro_actual:
        st.session_state._buscar_filtro = filtro_actual
        st.session_state._buscar_limite = _PASO_RESULTADOS
    limite = st.session_state.get("_buscar_limite", _PASO_RESULTADOS)
    mostrados = min(limite, len(resultados))

    st.caption(f"{len(resultados)} de {len(activos)} activos"
               + (f" · mostrando {mostrados}" if len(resultados) > mostrados else ""))

    en_lista = set(st.session_state.get("watchlist_simbolos", []))
    uid = (st.session_state.get("usuario_info") or {}).get("id")

    with st.container(height=400):
        for a in resultados[:mostrados]:
            c_info, c_abrir, c_add = st.columns([6, 1.2, 1.2], vertical_alignment="center")
            with c_info:
                st.markdown(
                    f"**{a['visible']}** · <span style='color:#8b949e; font-size:11px;'>"
                    f"{a['cat']}</span><br>"
                    f"<span style='color:#8b949e; font-size:12px;'>{a['desc']}</span>",
                    unsafe_allow_html=True,
                )
            with c_abrir:
                if st.button("Abrir", key=f"open_{a['name']}", width="stretch"):
                    # Abrir SÍ cierra el diálogo y refresca la app (carga el gráfico).
                    st.session_state.activo_seleccionado = a["name"]
                    st.session_state.mostrar_buscador = False
                    st.rerun()
            with c_add:
                if a["name"] in en_lista:
                    st.button("✓", key=f"add_{a['name']}", width="stretch", disabled=True,
                              help="Ya está en tu lista")
                else:
                    if st.button("➕", key=f"add_{a['name']}", width="stretch",
                                 help="Agregar a mi lista"):
                        _agregar_a_watchlist(uid, a)
                        # Rerun SOLO del diálogo (es un fragmento): refresca al instante
                        # para que la fila pase a "✓" y se limpie el tooltip. No cierra
                        # el modal ni reemplaza la app.
                        st.rerun(scope="fragment")

        # "Ver más" al final del scroll: revela otro bloque sin cerrar el modal
        if mostrados < len(resultados):
            restantes = len(resultados) - mostrados
            if st.button(f"Ver más ({restantes} restantes)", key="buscar_ver_mas",
                         width="stretch"):
                st.session_state._buscar_limite = limite + _PASO_RESULTADOS
                st.rerun(scope="fragment")
