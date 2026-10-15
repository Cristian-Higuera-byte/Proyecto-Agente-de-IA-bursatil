"""Vista "Resumen": cabecera y cuerpo en un fragmento que se refresca solo."""
import streamlit as st

from componentes_plataforma.flujo_vivo import intervalo as _intervalo
from componentes_plataforma.resumen.estilos import CSS
from componentes_plataforma.resumen.secciones import (curva_balance, exposicion_por_activo, nivel_margen, nota_pie,
                                          tarjetas_kpi)
from herramientas import estadisticas_portafolio
from herramientas.puente_mt5 import inicializar_mt5


def renderizar_panel_resumen(main=None):
    inicializar_mt5()
    st.html(CSS)

    with st.container(key="rs_wrap"):
        st.markdown(
            "<div class='rs-head'><div class='ic'><span class='rmi'>dashboard</span></div>"
            "<div><div class='rs-title'>Resumen</div>"
            "<div class='rs-sub'>Rendimiento y riesgo del portafolio en tiempo real</div></div></div>",
            unsafe_allow_html=True,
        )

        # Con el feed activo, los valores de CUENTA (equity, flotante, nivel de margen)
        # se pintan en vivo por el feed (data-pj-acc), sin rerun; el fragmento solo
        # recalcula lo que necesita cómputo (realizado, exposición, curva) cada pocos s.
        @st.fragment(run_every=_intervalo("2s", "4s"))
        def _cuerpo():
            s = estadisticas_portafolio.calcular()
            if "error" in s:
                st.warning("No se pudo conectar con MetaTrader 5. Abre el terminal "
                           "con la cuenta iniciada para ver tu portafolio.")
                return
            tarjetas_kpi(s)
            nivel_margen(s)
            curva_balance(s)
            exposicion_por_activo(s)
            nota_pie(s)

        _cuerpo()
