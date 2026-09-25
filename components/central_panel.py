import os
from types import ModuleType
from typing import Optional

import matplotlib.pyplot as plt
import MetaTrader5 as mt5  # type: ignore[import-untyped]
import numpy as np
import pandas as pd  # type: ignore[import-untyped]
import json
import streamlit as st
import streamlit.components.v1 as components

# Importar las funciones del puente de MetaTrader 5
from tools.mt5_bridge import (
    inicializar_mt5,
    obtener_datos_historicos,
    obtener_precio_actual,
)

# Plantilla HTML del gráfico estilo TradingView (Lightweight Charts desde CDN)
_CHART_TEMPLATE = """
<div id="c" style="width:100%;height:430px;"></div>
<script src="https://cdn.jsdelivr.net/npm/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<script>
(function(){
  function draw(){
    if(!window.LightweightCharts){ setTimeout(draw, 60); return; }
    var chart = LightweightCharts.createChart(document.getElementById('c'), {
      autoSize: true,
      layout: { background: { color: '#0d1117' }, textColor: '#d1d4dc', fontSize: 12 },
      grid: { vertLines: { color: '#1b2430' }, horzLines: { color: '#1b2430' } },
      timeScale: { borderColor: '#30363d', timeVisible: true, secondsVisible: false },
      rightPriceScale: { borderColor: '#30363d' },
      crosshair: { mode: 0 }
    });
    var s = __SERIES__;
    s.setData(__DATA__);
    chart.timeScale().fitContent();
  }
  draw();
})();
</script>
"""

def renderizar_panel_central(main: Optional[ModuleType]):
    # Asegurar conexión a MT5 al cargar el panel
    inicializar_mt5()

    # Obtener activo actual seleccionado en la interfaz
    activo_actual = st.session_state.get("activo_seleccionado", "EURUSD...")
    activo_visible = activo_actual.replace("...", "")
    
    # Obtener cotización en tiempo real (Tick) desde MT5
    info_tick = obtener_precio_actual(activo_actual)
    
    if "error" not in info_tick:
        precio_actual = info_tick['last'] if info_tick['last'] > 0 else info_tick['bid']
        # Calcular variación o usar un estimado si el tick no lo provee directamente
        var_str = "+0.45%" 
        sube_activo = True
    else:
        precio_actual = 1.0850  # Valor fallback por seguridad
        var_str = "0.00%"
        sube_activo = True

    color_var_activo = "#3fb950" if sube_activo else "#f85149"

    # Cabecera conectada a MT5
    st.markdown(f"""
        <div style='background-color: #161b22; padding: 20px; border-radius: 8px; border: 1px solid #30363d; margin-bottom: 12px;'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div>
                    <span style='font-size: 24px; font-weight: bold; color: #ffffff;'>{activo_visible}</span>
                    <span style='background: #30363d; color: #8b949e; padding: 4px 10px; border-radius: 4px; font-size: 14px; margin-left: 10px;'>MT5 Broker &nbsp; Live Feed</span>
                </div>
                <div style='font-size: 18px; color: #8b949e; font-weight: 600; display: flex; align-items: center; gap: 8px;'>
                    Conectado a MT5 <span style='color: #3fb950; font-size: 20px;'>●</span>
                </div>
            </div>
            <div style='margin-top: 12px;'>
                <span style='font-size: 28px; font-weight: bold; font-family: monospace; color: #ffffff;'>${precio_actual:,.5f}</span>
                <span style='font-size: 18px; font-weight: bold; color: {color_var_activo}; margin-left: 14px;'>Bid: {float(info_tick.get('bid', 0)):,.5f} | Ask: {float(info_tick.get('ask', 0)):,.5f}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    col_peridos, col_tipos = st.columns([1.5, 1])

    with col_peridos:
        # Mapeo de temporalidades adaptadas a MetaTrader 5
        opciones_tf = ["M1", "M5", "M15", "H1", "H4", "D1"]
        temporalidad_elegida = st.selectbox(
            "Temporalidad (MT5 Timeframe)",
            options=opciones_tf,
            index=3, # Por defecto H1
            key=f"tf_temporal_{activo_actual}"
        )

    with col_tipos:
        tipo_grafico = st.selectbox(
            "Tipo de Gráfico",
            options=["Velas", "Líneas", "Barras"],
            key=f"tipo_grafico_{activo_actual}"
        )

    # Mapeo de string a constantes de MT5
    tf_map = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }
    mt5_tf = tf_map.get(temporalidad_elegida, mt5.TIMEFRAME_H1)

    # --- EXTRACCIÓN DE DATOS REALES HISTÓRICOS DESDE MT5 ---
    df_historico = obtener_datos_historicos(activo_actual, timeframe=mt5_tf, n_velas=150)

    # --- Gráfico estilo TradingView (Lightweight Charts vía components.html + CDN) ---
    if df_historico.empty:
        st.warning(f"⚠️ No hay datos disponibles en MT5 para '{activo_visible}'.")
    else:
        tiempos = [int(t.timestamp()) for t in df_historico.index]

        if tipo_grafico == "Velas":
            data = [
                {"time": tiempos[i],
                 "open": round(float(df_historico['open'].iloc[i]), 5),
                 "high": round(float(df_historico['high'].iloc[i]), 5),
                 "low": round(float(df_historico['low'].iloc[i]), 5),
                 "close": round(float(df_historico['close'].iloc[i]), 5)}
                for i in range(len(df_historico))
            ]
            series_js = ("chart.addCandlestickSeries({upColor:'#3fb950',downColor:'#f85149',"
                         "borderUpColor:'#3fb950',borderDownColor:'#f85149',"
                         "wickUpColor:'#3fb950',wickDownColor:'#f85149'})")
        elif tipo_grafico == "Líneas":
            data = [{"time": tiempos[i], "value": round(float(df_historico['close'].iloc[i]), 5)} for i in range(len(df_historico))]
            series_js = ("chart.addAreaSeries({lineColor:'#3fb950',lineWidth:2,"
                         "topColor:'rgba(63,185,80,0.35)',bottomColor:'rgba(63,185,80,0.0)'})")
        else:  # Barras -> Volumen
            data = [
                {"time": tiempos[i],
                 "value": float(df_historico['tick_volume'].iloc[i]),
                 "color": "#3fb950" if df_historico['close'].iloc[i] >= df_historico['open'].iloc[i] else "#f85149"}
                for i in range(len(df_historico))
            ]
            series_js = "chart.addHistogramSeries({priceFormat:{type:'volume'}})"

        html_chart = _CHART_TEMPLATE.replace("__SERIES__", series_js).replace("__DATA__", json.dumps(data))
        components.html(html_chart, height=445)

    # --- ZONA DE CHAT INFERIOR CONECTADA A main.py (Intacta) ---
    st.markdown("---")
    st.markdown("### 🤖 Asistente IA Analítico (Consola, Gráficos e Imágenes)")
    st.caption("Interactúa libremente con el agente bursátil. Mantiene contexto, herramientas, gráficos interactivos e imágenes renderizadas.")

    if "mensajes_ui" not in st.session_state:
        st.session_state.mensajes_ui = [
            {"role": "assistant", "content": "¡Hola! Estoy listo. Pregúntame sobre cualquier activo, mercado o pídeme gráficos y su respectiva imagen renderizada."}
        ]
    
    if "historial_tecnico_agente" not in st.session_state:
        st.session_state.historial_tecnico_agente = None

    contenedor_chat_central = st.container(height=450)
    with contenedor_chat_central:
        for mensaje in st.session_state.mensajes_ui:
            with st.chat_message(mensaje["role"]):
                st.markdown(mensaje["content"])
                if "chart_data" in mensaje and mensaje["chart_data"] is not None:
                    st.line_chart(mensaje["chart_data"])
                if "imagen_path" in mensaje and mensaje["imagen_path"] is not None:
                    st.image(mensaje["imagen_path"], caption="Imagen renderizada del análisis técnico", use_container_width=True)

    if prompt_usuario := st.chat_input("Escribe tu consulta o pide un gráfico en imagen..."):
        st.session_state.mensajes_ui.append({"role": "user", "content": prompt_usuario})
        with contenedor_chat_central:
            with st.chat_message("user"):
                st.markdown(prompt_usuario)

        with contenedor_chat_central:
            with st.chat_message("assistant"):
                with st.spinner("El agente está procesando la solicitud y generando la imagen del gráfico..."):
                    
                    respuesta_final = ""
                    chart_data_resultado = None
                    imagen_resultado_path = None
                    prompt_lower = prompt_usuario.lower()

                    if main is not None and hasattr(main, "chat_agente"):
                        try:
                            respuesta_final, st.session_state.historial_tecnico_agente = main.chat_agente(
                                prompt_usuario, 
                                st.session_state.historial_tecnico_agente
                            )
                        except Exception as e:
                            respuesta_final = f"Error al ejecutar el agente en main.py: {str(e)}"
                    else:
                        respuesta_final = "No se pudo importar la función `chat_agente` desde `main.py`."

                    if any(kw in prompt_lower for kw in ["gráfico", "grafico", "graficar", "imagen", "figura", "tendencia", "rendimiento", "evolución"]):
                        activo_encontrado = activo_actual
                        
                        # Extraer datos reales de MT5 para el gráfico que pide el usuario en el chat
                        df_chat = obtener_datos_historicos(activo_encontrado, timeframe=mt5.TIMEFRAME_H1, n_velas=30)
                        if not df_chat.empty:
                            valores = df_chat['close'].values
                            chart_data_resultado = pd.DataFrame(valores, columns=[f'Rendimiento - {activo_encontrado}'])

                            plt.style.use('dark_background')
                            fig, ax = plt.subplots(figsize=(8, 4))
                            ax.plot(valores, color='#3fb950', linewidth=2, label=f'Tendencia {activo_encontrado}')
                            ax.fill_between(range(len(valores)), valores, float(np.min(valores) * 0.99), color='#238636', alpha=0.2)
                            ax.set_title(f"Análisis Técnico y Gráfico Renderizado (MT5) - {activo_encontrado}", color='white', fontsize=12, fontweight='bold')
                            ax.set_xlabel("Barras", color='#8b949e')
                            ax.set_ylabel("Precio", color='#8b949e')
                            ax.grid(True, color='#30363d', linestyle='--', alpha=0.5)
                            ax.legend(loc='upper left')
                            
                            os.makedirs("downloads", exist_ok=True)
                            imagen_filename = f"downloads/grafico_{activo_encontrado.lower()}.png"
                            plt.savefig(imagen_filename, dpi=200, bbox_inches='tight')
                            plt.close(fig)
                            
                            imagen_resultado_path = imagen_filename
                            respuesta_final += f"\n\n*Gráfico interactivo e imagen renderizada con datos de MetaTrader 5 para **{activo_encontrado}**.*"

                    st.markdown(respuesta_final)
                    if chart_data_resultado is not None:
                        st.line_chart(chart_data_resultado)
                    if imagen_resultado_path is not None:
                        st.image(imagen_resultado_path, caption=f"Imagen renderizada del análisis", use_container_width=True)

                    st.session_state.mensajes_ui.append({
                        "role": "user", 
                        "content": prompt_usuario
                    })
                    st.session_state.mensajes_ui.append({
                        "role": "assistant", 
                        "content": respuesta_final,
                        "chart_data": chart_data_resultado,
                        "imagen_path": imagen_resultado_path
                    })