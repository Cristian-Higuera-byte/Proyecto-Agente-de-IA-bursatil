"""
buscador/datos.py
-----------------
Datos y lógica del buscador (sin UI): carga de TODOS los símbolos del broker MT5
(cacheada 10 min), categorías, filtro por texto/categoría y alta de un activo en la
watchlist del usuario. `_agregar_a_watchlist` lo reutiliza también mercados_panel.py.
"""
import streamlit as st
import MetaTrader5 as mt5  # type: ignore[import-untyped]

from herramientas.puente_mt5 import MT5_LOCK, inicializar_mt5
from herramientas import gestor_lista_activos as wl


@st.cache_data(ttl=600, show_spinner=False)
def cargar_simbolos_broker() -> list[dict]:
    """Todos los símbolos del broker MT5: {name, visible, desc, cat}. Cache 10 min."""
    inicializar_mt5()
    with MT5_LOCK:
        simbolos = mt5.symbols_get()
    salida: list[dict] = []
    if simbolos:
        for s in simbolos:
            salida.append({
                "name": s.name,                                  # exacto (MT5 / gráfico)
                "visible": wl.nombre_visible(s.name),            # nombre mostrado
                "desc": (s.description or s.name).strip(),
                "cat": wl.categoria_simbolo(getattr(s, "path", ""), s.name),
            })
    salida.sort(key=lambda x: x["visible"])
    return salida


def categorias(activos: list[dict]) -> list[str]:
    return ["Todo"] + sorted({a["cat"] for a in activos})


def filtrar(activos: list[dict], q: str, cat: str) -> list[dict]:
    q = (q or "").strip().upper()
    res = []
    for a in activos:
        if cat and cat != "Todo" and a["cat"] != cat:
            continue
        if q and q not in a["visible"].upper() and q not in a["name"].upper() and q not in a["desc"].upper():
            continue
        res.append(a)
    return res


def _agregar_a_watchlist(uid, a: dict):
    """Agrega el activo a la lista SIN llamar a MT5 (la API no es thread-safe y
    chocaría con los fragmentos de precios en vivo → pantalla en blanco).
    Se usa la info ya cacheada del buscador; el precio real lo pone el fragmento
    `actualizar_precios_mt5` en el siguiente tick."""
    name = a["name"]
    wl.agregar_simbolo(uid, name)
    datos = st.session_state.setdefault("datos_mercado_real", {})
    if name not in datos:
        datos[name] = {
            "nombre": a.get("desc") or a.get("visible") or name,
            "mercado": a.get("cat", "OTROS"),
            "precio": 0.0,
            "var": "+0.00 (0.00%)",
            "sube": True,
        }
    lista = st.session_state.setdefault("watchlist_simbolos", [])
    if name not in lista:
        lista.append(name)
