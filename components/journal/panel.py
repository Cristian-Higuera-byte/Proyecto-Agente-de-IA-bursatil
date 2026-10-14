"""Vista "Diario": cabecera, tabla de operaciones con métricas, ficha por operación y nota al pie."""
import streamlit as st

from components.journal.estilos import CSS
from components.journal.ficha import ficha
from components.journal.tabla import tabla_y_metricas
from tools import journal_stats
from tools.mt5_bridge import inicializar_mt5, obtener_info_cuenta


def renderizar_panel_journal(main=None):
    inicializar_mt5()
    st.html(CSS)
    with st.container(key="jr_wrap"):
        st.html(
            "<div class='jr-head'><div class='ic'><span class='jrmi'>menu_book</span></div>"
            "<div><div class='jr-title'>Diario</div>"
            "<div class='jr-sub'>Trading journal: registro automático, métricas y notas por operación</div>"
            "</div></div>"
        )
        info_c = obtener_info_cuenta()
        m = info_c.get("currency", "USD") if isinstance(info_c, dict) else "USD"
        jd = journal_stats.calcular()
        tabla_y_metricas(m, jd["operaciones"], jd["stats"])
        ficha(m, jd["operaciones"])
        st.html(
            "<div class='jr-note'>Operaciones reconstruidas emparejando los deals de "
            "entrada y salida de MetaTrader 5. El R/R planificado aparece en operaciones "
            "abiertas con SL/TP; la captura es un mini-gráfico generado automáticamente.</div>"
        )
