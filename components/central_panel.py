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

# ==========================================================================
# Plantilla HTML del gráfico estilo TradingView (Lightweight Charts + polling
# al servidor local de MT5: servidor_datos.py).
#
# Funcional: velas/línea/histograma, panel de volumen permanente, leyenda
#            OHLC dinámica, selector de rango inferior, indicador SMA(20),
#            captura de imagen y pantalla completa.
# Decorativo (marcado "Próximamente"): iconos de dibujo de la barra
#            izquierda -- lightweight-charts no incluye herramientas de
#            dibujo nativas, eso requeriría un desarrollo aparte.
# ==========================================================================
_CHART_TEMPLATE = """
<style>
    #tv-wrap { background:#0d1117; border:1px solid #30363d; border-radius:8px; overflow:hidden; }
    #tv-topbar {
        display:flex; align-items:center; justify-content:space-between;
        padding:8px 12px; border-bottom:1px solid #1b2430; background:#0d1117;
        font-family:-apple-system,"Segoe UI",Roboto,Arial,sans-serif;
    }
    #tv-legend { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
    #tv-legend .tv-sym { font-size:14px; font-weight:700; color:#ffffff; }
    #tv-legend .tv-ohlc { font-size:12px; color:#8b949e; font-family:monospace; }
    #tv-legend .tv-ohlc b { font-weight:700; }
    #tv-legend .tv-vol { font-size:12px; color:#8b949e; font-family:monospace; }

    #tv-actions { display:flex; align-items:center; gap:4px; }
    .tvbtn {
        display:flex; align-items:center; gap:6px;
        background:transparent; border:1px solid transparent; color:#8b949e;
        font-size:12px; padding:5px 9px; border-radius:6px; cursor:pointer;
        transition: background .15s ease, color .15s ease;
    }
    .tvbtn:hover { background:rgba(255,255,255,0.08); color:#ffffff; }
    .tvbtn.activo { background:rgba(139,92,246,0.15); color:#a78bfa; border-color:rgba(139,92,246,0.4); }

    #tv-body { display:flex; }
    #tv-toolbar-left {
        display:flex; flex-direction:column; align-items:center; gap:4px;
        padding:8px 3px; border-right:1px solid #1b2430; background:#0d1117;
    }
    .tvtool {
        width:28px; height:28px; display:flex; align-items:center; justify-content:center;
        background:transparent; border:none; color:#8b949e; font-size:14px;
        border-radius:6px; cursor:pointer; transition: background .15s ease, color .15s ease;
    }
    .tvtool:hover { background:rgba(255,255,255,0.08); color:#ffffff; }
    .tvtool.active { background:rgba(139,92,246,0.18); color:#a78bfa; }

    #c { flex:1; height:480px; }

    #tv-rangebar {
        display:flex; align-items:center; gap:2px; padding:6px 10px;
        border-top:1px solid #1b2430; background:#0d1117;
        font-family:-apple-system,"Segoe UI",Roboto,Arial,sans-serif;
    }
    .tvrange {
        background:transparent; border:none; color:#8b949e; font-size:12px;
        font-weight:600; padding:5px 10px; border-radius:5px; cursor:pointer;
    }
    .tvrange:hover { background:rgba(255,255,255,0.08); color:#ffffff; }
    .tvrange.active { background:rgba(88,166,255,0.15); color:#58a6ff; }
</style>

<div id="tv-wrap">
    <div id="tv-topbar">
        <div id="tv-legend">
            <span class="tv-sym">__SIMBOLO__</span>
            <span class="tv-ohlc" id="tv-ohlc-vals">Cargando…</span>
            <span class="tv-vol" id="tv-vol-val"></span>
        </div>
        <div id="tv-actions">
            <button class="tvbtn" id="btn-ind" title="Activar/desactivar media móvil SMA 20">📈 Indicadores</button>
            <button class="tvbtn" id="btn-shot" title="Descargar imagen del gráfico">📷</button>
            <button class="tvbtn" id="btn-full" title="Pantalla completa">⛶</button>
        </div>
    </div>
    <div id="tv-body">
        <div id="tv-toolbar-left">
            <button class="tvtool active" id="tool-cross" title="Cursor / Cruz">✛</button>
            <button class="tvtool" title="Línea de tendencia (próximamente)">📈</button>
            <button class="tvtool" title="Línea horizontal (próximamente)">➖</button>
            <button class="tvtool" title="Fibonacci (próximamente)">🔢</button>
            <button class="tvtool" title="Texto (próximamente)">🔤</button>
            <button class="tvtool" title="Pincel (próximamente)">🖌️</button>
            <button class="tvtool" title="Regla / medir (próximamente)">📏</button>
            <button class="tvtool" title="Bloquear dibujos (próximamente)">🔒</button>
            <button class="tvtool" title="Borrar dibujos (próximamente)">🗑️</button>
        </div>
        <div id="c"></div>
    </div>
    <div id="tv-rangebar">
        <button class="tvrange" data-range="1D">1D</button>
        <button class="tvrange" data-range="5D">5D</button>
        <button class="tvrange" data-range="1M">1M</button>
        <button class="tvrange" data-range="3M">3M</button>
        <button class="tvrange" data-range="6M">6M</button>
        <button class="tvrange" data-range="YTD">YTD</button>
        <button class="tvrange" data-range="1A">1A</button>
        <button class="tvrange" data-range="5A">5A</button>
        <button class="tvrange active" data-range="Todos">Todos</button>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<script>
(function(){
  var API = "http://localhost:8000";
  var SIMBOLO = "__SIMBOLO_API__";
  var TF = "__TF__";
  var TIPO = "__TIPO__";

  var BARS_POR_DIA = { M1: 1440, M5: 288, M15: 96, H1: 24, H4: 6, D1: 1 }[TF] || 24;

  function iniciar(){
    if(!window.LightweightCharts){ setTimeout(iniciar, 60); return; }

    var chart = LightweightCharts.createChart(document.getElementById('c'), {
      autoSize: true,
      layout: { background: { color: '#0d1117' }, textColor: '#d1d4dc', fontSize: 12 },
      grid: { vertLines: { color: '#161b22' }, horzLines: { color: '#161b22' } },
      timeScale: { borderColor: '#30363d', timeVisible: true, secondsVisible: false },
      rightPriceScale: { borderColor: '#30363d' },
      crosshair: { mode: 1 }
    });

    // --- Serie principal (según el tipo elegido) ---
    var serie;
    if (TIPO === "Líneas") {
      serie = chart.addAreaSeries({ lineColor:'#3fb950', lineWidth:2, topColor:'rgba(63,185,80,0.35)', bottomColor:'rgba(63,185,80,0.0)' });
    } else if (TIPO === "Barras") {
      serie = chart.addHistogramSeries({ priceFormat: { type: 'volume' } });
    } else {
      serie = chart.addCandlestickSeries({ upColor:'#3fb950', downColor:'#f85149', borderUpColor:'#3fb950', borderDownColor:'#f85149', wickUpColor:'#3fb950', wickDownColor:'#f85149' });
    }
    serie.priceScale().applyOptions({ scaleMargins: { top: 0.08, bottom: 0.22 } });

    // --- Panel de volumen permanente, debajo del precio (como TradingView) ---
    var serieVolumen = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: 'vol',
      color: 'rgba(63,185,80,0.5)'
    });
    chart.priceScale('vol').applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });

    var lineaSMA = null;
    var indicadoresActivos = false;
    var datosActuales = [];

    function aPunto(v){
      if (TIPO === "Líneas") return { time: v.time, value: v.close };
      if (TIPO === "Barras") return { time: v.time, value: v.volume, color: (v.close >= v.open ? '#3fb950' : '#f85149') };
      return { time: v.time, open: v.open, high: v.high, low: v.low, close: v.close };
    }
    function aPuntoVolumen(v){
      return { time: v.time, value: v.volume || 0, color: (v.close >= v.open ? 'rgba(63,185,80,0.5)' : 'rgba(248,81,73,0.5)') };
    }
    function fmtVol(v){
      v = v || 0;
      if (v >= 1e9) return (v/1e9).toFixed(2) + 'B';
      if (v >= 1e6) return (v/1e6).toFixed(2) + 'M';
      if (v >= 1e3) return (v/1e3).toFixed(2) + 'K';
      return String(v);
    }
    function calcularSMA(datos, periodo){
      var out = [];
      for (var i = periodo - 1; i < datos.length; i++){
        var suma = 0;
        for (var j = i - periodo + 1; j <= i; j++){ suma += datos[j].close; }
        out.push({ time: datos[i].time, value: suma / periodo });
      }
      return out;
    }

    function actualizarLeyenda(v){
      if (!v) return;
      var elOhlc = document.getElementById('tv-ohlc-vals');
      var elVol = document.getElementById('tv-vol-val');
      if (!elOhlc) return;
      var sube = v.close >= v.open;
      var color = sube ? '#3fb950' : '#f85149';
      var variacion = v.open ? (((v.close - v.open) / v.open) * 100) : 0;
      elOhlc.innerHTML =
        'O<b style="color:' + color + '">' + v.open.toFixed(5) + '</b> ' +
        'H<b style="color:' + color + '">' + v.high.toFixed(5) + '</b> ' +
        'L<b style="color:' + color + '">' + v.low.toFixed(5) + '</b> ' +
        'C<b style="color:' + color + '">' + v.close.toFixed(5) + '</b> ' +
        '<b style="color:' + color + '">' + (variacion >= 0 ? '+' : '') + variacion.toFixed(2) + '%</b>';
      if (elVol) elVol.innerText = 'Vol. ' + fmtVol(v.volume);
    }

    function aplicarSMA(){
      if (lineaSMA) { chart.removeSeries(lineaSMA); lineaSMA = null; }
      lineaSMA = chart.addLineSeries({ color: '#f5c518', lineWidth: 2, priceLineVisible: false, lastValueVisible: false });
      lineaSMA.setData(calcularSMA(datosActuales, 20));
    }

    function cargar(n){
      fetch(API + "/velas/" + encodeURIComponent(SIMBOLO) + "?tf=" + TF + "&n=" + n)
        .then(function(r){ return r.json(); })
        .then(function(velas){
          if (velas && velas.length){
            datosActuales = velas;
            serie.setData(velas.map(aPunto));
            serieVolumen.setData(velas.map(aPuntoVolumen));
            chart.timeScale().fitContent();
            actualizarLeyenda(velas[velas.length - 1]);
            if (indicadoresActivos) aplicarSMA();
          }
        })
        .catch(function(){});
    }

    // 1) Carga inicial
    cargar(150);

    // 2) EN VIVO: cada 1.5 s pide la última vela y avanza el gráfico
    setInterval(function(){
      fetch(API + "/ultima/" + encodeURIComponent(SIMBOLO) + "?tf=" + TF)
        .then(function(r){ return r.json(); })
        .then(function(v){
          if (v && v.time){
            serie.update(aPunto(v));
            serieVolumen.update(aPuntoVolumen(v));
            if (datosActuales.length && datosActuales[datosActuales.length - 1].time === v.time){
              datosActuales[datosActuales.length - 1] = v;
            } else {
              datosActuales.push(v);
            }
            actualizarLeyenda(v);
          }
        })
        .catch(function(){});
    }, 1500);

    // Leyenda dinámica al pasar el cursor sobre el gráfico
    chart.subscribeCrosshairMove(function(param){
      if (!param || !param.time){
        if (datosActuales.length) actualizarLeyenda(datosActuales[datosActuales.length - 1]);
        return;
      }
      var idx = datosActuales.findIndex(function(d){ return d.time === param.time; });
      if (idx >= 0) actualizarLeyenda(datosActuales[idx]);
    });

    // Selector de rango inferior: vuelve a consultar el servidor con más/menos velas
    var diasPorRango = { "1D": 1, "5D": 5, "1M": 22, "3M": 66, "6M": 132, "1A": 252, "5A": 1260 };
    document.querySelectorAll('.tvrange').forEach(function(btn){
      btn.addEventListener('click', function(){
        document.querySelectorAll('.tvrange').forEach(function(b){ b.classList.remove('active'); });
        btn.classList.add('active');
        var rango = btn.getAttribute('data-range');
        if (rango === 'Todos'){ cargar(5000); return; }
        if (rango === 'YTD'){
          var inicioAnio = Date.UTC(new Date().getUTCFullYear(), 0, 1) / 1000;
          var dias = Math.max(1, Math.ceil((Date.now() / 1000 - inicioAnio) / 86400));
          cargar(Math.min(5000, dias * BARS_POR_DIA));
          return;
        }
        var dias = diasPorRango[rango] || 30;
        cargar(Math.min(5000, Math.max(10, dias * BARS_POR_DIA)));
      });
    });

    // Indicador SMA(20) activable
    var btnInd = document.getElementById('btn-ind');
    if (btnInd){
      btnInd.addEventListener('click', function(){
        indicadoresActivos = !indicadoresActivos;
        btnInd.classList.toggle('activo', indicadoresActivos);
        if (indicadoresActivos) aplicarSMA();
        else if (lineaSMA){ chart.removeSeries(lineaSMA); lineaSMA = null; }
      });
    }

    // Captura de imagen del gráfico
    var btnShot = document.getElementById('btn-shot');
    if (btnShot){
      btnShot.addEventListener('click', function(){
        try {
          var canvas = chart.takeScreenshot();
          var enlace = document.createElement('a');
          enlace.download = SIMBOLO + '_grafico.png';
          enlace.href = canvas.toDataURL();
          enlace.click();
        } catch (e) {}
      });
    }

    // Pantalla completa
    var btnFull = document.getElementById('btn-full');
    var wrap = document.getElementById('tv-wrap');
    if (btnFull && wrap){
      btnFull.addEventListener('click', function(){
        if (!document.fullscreenElement){
          if (wrap.requestFullscreen) wrap.requestFullscreen();
        } else {
          document.exitFullscreen();
        }
      });
    }
  }
  iniciar();
})();
</script>
"""

def renderizar_panel_central(main: Optional[ModuleType]):
    # Asegurar conexión a MT5 al cargar el panel
    inicializar_mt5()

    # Obtener activo actual seleccionado y limpiar los puntos suspensivos para MT5
    activo_actual = st.session_state.get("activo_seleccionado", "EURUSD...")
    activo_visible = activo_actual.replace("...", "").strip()

    # Cabecera con PRECIO EN VIVO: se refresca sola cada 2 s usando el símbolo limpio
    @st.fragment(run_every="2s")
    def _cabecera_precio():
        # Usar el símbolo COMPLETO (con "...") para MT5: el broker nombra así
        # los pares de Forex/metales. Con el símbolo "limpio" no los encuentra.
        info_tick = obtener_precio_actual(activo_actual)
        if "error" not in info_tick:
            precio_actual = info_tick.get("last", 0) if info_tick.get("last", 0) > 0 else info_tick.get("bid", 0)
        else:
            precio_actual = 0.0
        # Color según el precio suba o baje respecto a la lectura anterior
        clave = f"_prev_precio_{activo_visible}"
        anterior = st.session_state.get(clave, precio_actual)
        sube_activo = precio_actual >= anterior
        st.session_state[clave] = precio_actual
        color_var_activo = "#3fb950" if sube_activo else "#f85149"
        bid = float(info_tick.get("bid", 0))
        ask = float(info_tick.get("ask", 0))
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
                    <span style='font-size: 28px; font-weight: bold; font-family: monospace; color: {color_var_activo};'>${precio_actual:,.5f}</span>
                    <span style='font-size: 18px; font-weight: bold; color: {color_var_activo}; margin-left: 14px;'>Bid: {bid:,.5f} | Ask: {ask:,.5f}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    _cabecera_precio()

    col_peridos, col_tipos = st.columns([1.5, 1])

    with col_peridos:
        opciones_tf = ["M1", "M5", "M15", "H1", "H4", "D1"]
        temporalidad_elegida = st.selectbox(
            "Temporalidad (MT5 Timeframe)",
            options=opciones_tf,
            index=3,
            key=f"tf_temporal_{activo_visible}"
        )

    with col_tipos:
        tipo_grafico = st.selectbox(
            "Tipo de Gráfico",
            options=["Velas", "Líneas", "Barras"],
            key=f"tipo_grafico_{activo_visible}"
        )

    # --- Gráfico EN TIEMPO REAL, estilo TradingView, usando el símbolo limpio ---
    html_chart = (
        _CHART_TEMPLATE
        .replace("__SIMBOLO_API__", activo_actual)   # símbolo COMPLETO para pedir datos a MT5
        .replace("__SIMBOLO__", activo_visible)       # nombre limpio solo para mostrar en la leyenda
        .replace("__TF__", temporalidad_elegida)
        .replace("__TIPO__", tipo_grafico)
    )
    components.html(html_chart, height=600)

    # --- ZONA DE CHAT INFERIOR CONECTADA A main.py ---
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
                        activo_encontrado = activo_visible  # nombre para mostrar

                        # Datos con el símbolo COMPLETO (con "...") para que MT5 lo encuentre
                        df_chat = obtener_datos_historicos(activo_actual, timeframe=mt5.TIMEFRAME_H1, n_velas=30)
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