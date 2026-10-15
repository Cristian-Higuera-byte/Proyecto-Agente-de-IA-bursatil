"""Carga inicial del mercado: índices globales (yfinance), watchlist del usuario y datos de cada símbolo."""
import copy
import math
from pathlib import Path

import streamlit as st

from componentes_plataforma._estaticos import datos_json
from componentes_plataforma.mercado_datos.entrada import construir_entrada
from componentes_plataforma.mercado_datos.sparkline import asegurar_semilla
from herramientas import gestor_lista_activos as wl
from herramientas.puente_mt5 import inicializar_mt5

# Valores de respaldo de la barra de índices y su símbolo en yfinance (indices_globales.json)
_INDICES = datos_json(Path(__file__).parent / "indices_globales.json")


def cargar_datos_mercado():
    # Inicializar conexión a MT5 de forma segura al cargar el mercado
    inicializar_mt5()

    # Si ya se cargó una vez, no repetir el fetch pesado; los fragmentos
    # (actualizar_precios_mt5) mantienen los precios en vivo.
    if st.session_state.get("datos_cargados"):
        return

    # 1. Índices globales (barra superior) — se mantiene con yfinance
    if "datos_indices_globales" not in st.session_state:
        st.session_state.datos_indices_globales = copy.deepcopy(_INDICES["defecto"])
    try:
        import yfinance as yf  # type: ignore[import-untyped]
        simbolos_indices = _INDICES["yfinance"]
        for key, sym in simbolos_indices.items():
            hist = yf.Ticker(sym).history(period="3d")
            if not hist.empty and "Close" in hist.columns:
                val = hist["Close"].iloc[-1]
                if not math.isnan(float(val)):
                    actual = float(val)
                    anterior_val = hist["Close"].iloc[-2] if len(hist) > 1 else actual
                    anterior = float(anterior_val) if not math.isnan(float(anterior_val)) else actual
                    cambio = actual - anterior
                    porc = (cambio / anterior * 100) if anterior != 0 else 0.0
                    st.session_state.datos_indices_globales[key] = {
                        "valor": actual, "var": f"{'+' if cambio >= 0 else ''}{porc:.2f}%", "sube": cambio >= 0}
    except Exception:
        pass

    # 2. Watchlist del USUARIO (desde Supabase; si es nuevo, se siembra el default)
    usuario = st.session_state.get("usuario_info", {})
    uid = usuario.get("id") if isinstance(usuario, dict) else None
    simbolos = wl.obtener_watchlist(uid)
    if not simbolos:
        simbolos = wl.sembrar_defaults(uid)
    st.session_state.watchlist_simbolos = simbolos

    # 3. Construir los datos de mercado de esos símbolos (nombre EXACTO para MT5)
    datos = {}
    for sym in simbolos:
        datos[sym] = construir_entrada(sym)
        # Sembrar el sparkline con histórico M1 (se reintenta si vino vacío)
        asegurar_semilla(sym)
    st.session_state.datos_mercado_real = datos

    st.session_state.datos_cargados = True
