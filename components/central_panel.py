import os
from types import ModuleType
from typing import Optional

import matplotlib.pyplot as plt
import MetaTrader5 as mt5  # type: ignore[import-untyped]
import numpy as np
import pandas as pd  # type: ignore[import-untyped]
import streamlit as st
import streamlit.components.v1 as components

# Importar las funciones del puente de MetaTrader 5
from tools.mt5_bridge import (
    inicializar_mt5,
    obtener_datos_historicos,
    obtener_precio_actual,
    resolver_simbolo,
)

# ==========================================================================
# Plantilla HTML del gráfico con Indicadores y Herramientas de Dibujo Interactivas
# ==========================================================================
_CHART_TEMPLATE = """
<style>
    body { background-color: #0d1117; margin: 0; padding: 0; color: #d1d4dc; }
    #tv-wrap { background:#0d1117; border:1px solid #30363d; border-radius:8px; overflow:hidden; display:flex; flex-direction:column; height:100vh; box-sizing:border-box; }
    
    #tv-wrap:fullscreen {
        border: none; border-radius: 0; width: 100vw; height: 100vh; background: #0d1117;
    }
    #tv-wrap:-webkit-full-screen {
        border: none; border-radius: 0; width: 100vw; height: 100vh; background: #0d1117;
    }

    #tv-topbar {
        display:flex; align-items:center; justify-content:space-between;
        padding:10px 14px; border-bottom:1px solid #1b2430; background:#0d1117;
        font-family:-apple-system,"Segoe UI",Roboto,Arial,sans-serif;
        flex-shrink: 0; z-index: 50;
    }
    #tv-legend { display:flex; align-items:center; gap:12px; flex-wrap:wrap; }
    #tv-legend .tv-sym { font-size:15px; font-weight:700; color:#ffffff; }
    #tv-legend .tv-ohlc { font-size:12px; color:#8b949e; font-family:monospace; }
    #tv-legend .tv-ohlc b { font-weight:700; }
    #tv-legend .tv-vol { font-size:12px; color:#8b949e; font-family:monospace; }

    #tv-actions { display:flex; align-items:center; gap:8px; }
    .tvbtn {
        display:flex; align-items:center; gap:6px;
        background:rgba(255,255,255,0.04); border:1px solid #30363d; color:#c9d1d9;
        font-size:13px; font-weight:500; padding:6px 12px; border-radius:6px; cursor:pointer;
        transition: background .15s ease, color .15s ease, border-color .15s ease;
    }
    .tvbtn:hover { background:rgba(255,255,255,0.08); color:#ffffff; border-color:#8b949e; }
    .tvbtn.activo { background:rgba(139,92,246,0.2); color:#a78bfa; border-color:rgba(139,92,246,0.5); }

    /* Menús desplegables */
    .tv-dropdown { position: relative; display: inline-block; }
    .tv-dropdown-content {
        display: none; position: absolute; right: 0; top: 100%;
        background-color: #161b22; min-width: 210px;
        box-shadow: 0px 8px 24px rgba(0,0,0,0.6);
        z-index: 1000; border: 1px solid #30363d; border-radius: 6px; padding: 4px 0;
    }
    .tv-dropdown-content.show { display: block; }
    .tv-drop-item {
        color: #d1d4dc; padding: 9px 14px; text-decoration: none; display: flex;
        align-items: center; justify-content: space-between; font-size: 13px; cursor: pointer;
        transition: background 0.1s;
    }
    .tv-drop-item:hover { background-color: rgba(139,92,246,0.2); color: #a78bfa; }
    .tv-drop-item span.status { font-size: 11px; opacity: 0.6; }
    .tv-drop-item.active-ind span.status { color: #3fb950; opacity: 1; font-weight: bold; }

    #tv-body { display:flex; flex: 1; position: relative; overflow: hidden; flex-direction: column; }
    #tv-main-canvas-area { display: flex; flex: 1; position: relative; overflow: hidden; }
    
    #tv-toolbar-left {
        display:flex; flex-direction:column; align-items:center; gap:4px;
        padding:8px 4px; border-right:1px solid #1b2430; background:#0d1117;
        flex-shrink: 0; z-index: 20;
    }
    .tvtool {
        width:30px; height:30px; display:flex; align-items:center; justify-content:center;
        background:transparent; border:none; color:#8b949e; font-size:14px;
        border-radius:6px; cursor:pointer; transition: background .15s ease, color .15s ease;
    }
    .tvtool:hover { background:rgba(255,255,255,0.08); color:#ffffff; }
    .tvtool.active { background:rgba(139,92,246,0.18); color:#a78bfa; }

    /* Contenedor del gráfico y capa de dibujo con interacción de datos */
    #chart-wrapper { flex:1; position: relative; width: 100%; height: 100%; display: flex; flex-direction: column; }
    #c { flex:1; width: 100%; height: 100%; }
    
    #drawing-canvas {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 10;
    }

    #rsi-container { height: 110px; width: 100%; border-top: 1px solid #1b2430; display: none; }

    #tv-rangebar {
        display:flex; align-items:center; gap:4px; padding:8px 12px;
        border-top:1px solid #1b2430; background:#0d1117;
        font-family:-apple-system,"Segoe UI",Roboto,Arial,sans-serif;
        flex-shrink: 0; overflow-x: auto; z-index: 20;
    }
    .tvrange {
        background:transparent; border:1px solid transparent; color:#8b949e; font-size:13px;
        font-weight:600; padding:6px 12px; border-radius:6px; cursor:pointer; white-space: nowrap;
        transition: background .15s ease, color .15s ease, border-color .15s ease;
    }
    .tvrange:hover { background:rgba(255,255,255,0.08); color:#ffffff; }
    .tvrange.active { background:rgba(88,166,255,0.18); color:#58a6ff; border-color:rgba(88,166,255,0.3); }
</style>

<div id="tv-wrap">
    <div id="tv-topbar">
        <div id="tv-legend">
            <span class="tv-sym">__SIMBOLO__</span>
            <span class="tv-ohlc" id="tv-ohlc-vals">Cargando…</span>
            <span class="tv-vol" id="tv-vol-val"></span>
        </div>
        <div id="tv-actions">
            <!-- Selector Tipo de Gráfico -->
            <div class="tv-dropdown" id="type-dropdown">
                <button class="tvbtn activo" id="btn-type-select" title="Cambiar tipo de gráfico">🕯️ Velas ▾</button>
                <div class="tv-dropdown-content" id="type-menu">
                    <div class="tv-drop-item" data-type="candlestick">🕯 Velas Japonesas</div>
                    <div class="tv-drop-item" data-type="hollow">🕯 Velas Huecas</div>
                    <div class="tv-drop-item" data-type="bars">📊 Barras (OHLC)</div>
                    <div class="tv-drop-item" data-type="line">📈 Línea</div>
                    <div class="tv-drop-item" data-type="area">📉 Área</div>
                    <div class="tv-drop-item" data-type="heikin">🔥 Heikin Ashi</div>
                </div>
            </div>

            <!-- Selector de Indicadores Funcionales -->
            <div class="tv-dropdown" id="ind-dropdown">
                <button class="tvbtn" id="btn-ind-select" title="Añadir indicadores técnicos">📈 Indicadores ▾</button>
                <div class="tv-dropdown-content" id="ind-menu">
                    <div class="tv-drop-item" data-ind="sma20"><span>SMA 20 (Media Simple)</span><span class="status" id="st-sma20">Off</span></div>
                    <div class="tv-drop-item" data-ind="sma50"><span>SMA 50 (Media Simple)</span><span class="status" id="st-sma50">Off</span></div>
                    <div class="tv-drop-item" data-ind="ema20"><span>EMA 20 (Media Exponencial)</span><span class="status" id="st-ema20">Off</span></div>
                    <div class="tv-drop-item" data-ind="bollinger"><span>Bandas de Bollinger (20,2)</span><span class="status" id="st-bollinger">Off</span></div>
                    <div class="tv-drop-item" data-ind="rsi"><span>RSI (14) - Oscilador</span><span class="status" id="st-rsi">Off</span></div>
                </div>
            </div>

            <button class="tvbtn" id="btn-shot" title="Descargar imagen del gráfico">📷</button>
            <button class="tvbtn" id="btn-full" title="Pantalla completa">⛶</button>
        </div>
    </div>
    
    <div id="tv-body">
        <div id="tv-main-canvas-area">
            <div id="tv-toolbar-left">
                <button class="tvtool active" id="tool-cross" data-tool="cross" title="Cursor / Cruz">✛</button>
                <button class="tvtool" id="tool-trend" data-tool="trend" title="Línea de tendencia">📈</button>
                <button class="tvtool" id="tool-hline" data-tool="hline" title="Línea horizontal">➖</button>
                <button class="tvtool" id="tool-fib" data-tool="fib" title="Retrocesos de Fibonacci">🔢</button>
                <button class="tvtool" id="tool-text" data-tool="text" title="Herramienta de Texto">🔤</button>
                <button class="tvtool" id="tool-measure" data-tool="measure" title="Regla de medición">📏</button>
                <button class="tvtool" id="tool-lock" data-tool="lock" title="Bloquear dibujos">🔒</button>
                <button class="tvtool" id="tool-clear" data-tool="clear" title="Limpiar elementos">🗑</button>
            </div>
            <div id="chart-wrapper">
                <div id="c"></div>
                <canvas id="drawing-canvas"></canvas>
            </div>
        </div>
        <div id="rsi-container"></div>
    </div>

    <div id="tv-rangebar">
        <button class="tvrange" data-tf="M1" data-n="1440">M1</button>
        <button class="tvrange" data-tf="M5" data-n="1440">M5</button>
        <button class="tvrange" data-tf="M15" data-n="960">M15</button>
        <button class="tvrange active" data-tf="H1" data-n="720">H1</button>
        <button class="tvrange" data-tf="H4" data-n="360">H4</button>
        <button class="tvrange" data-tf="H1" data-n="24">1D</button>
        <button class="tvrange" data-tf="H1" data-n="120">5D</button>
        <button class="tvrange" data-tf="D1" data-n="22">1M</button>
        <button class="tvrange" data-tf="D1" data-n="66">3M</button>
        <button class="tvrange" data-tf="D1" data-n="132">6M</button>
        <button class="tvrange" data-tf="D1" data-n="252">1A</button>
        <button class="tvrange" data-tf="D1" data-n="5000">Todos</button>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<script>
(function(){
  var API = "http://localhost:8000";
  var SIMBOLO = "__SIMBOLO__";

  var tfActual = "H1";
  var nBarrasActual = 720;
  var tipoActual = "candlestick";
  var datosActuales = [];

  // Estado de los indicadores
  var indicadores = { sma20: false, sma50: false, ema20: false, bollinger: false, rsi: false };
  var seriesInd = { sma20: null, sma50: null, ema20: null, bolpper: null, bolpmedia: null, bolpsuper: null };

  var chartRsi = null;
  var serieRsi = null;

  function iniciar(){
    if(!window.LightweightCharts){ setTimeout(iniciar, 60); return; }

    var containerEl = document.getElementById('c');
    var chart = LightweightCharts.createChart(containerEl, {
      autoSize: true,
      layout: { background: { color: '#0d1117' }, textColor: '#d1d4dc', fontSize: 12 },
      grid: { vertLines: { color: '#161b22' }, horzLines: { color: '#161b22' } },
      timeScale: { borderColor: '#30363d', timeVisible: true, secondsVisible: false },
      rightPriceScale: { borderColor: '#30363d' },
      crosshair: { mode: 1 }
    });

    var serie = null;
    var serieVolumen = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: 'vol',
      color: 'rgba(63,185,80,0.5)'
    });
    chart.priceScale('vol').applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });

    function crearSerie(tipo){
      if (serie) { chart.removeSeries(serie); }
      if (tipo === "candlestick") {
        serie = chart.addCandlestickSeries({ upColor:'#3fb950', downColor:'#f85149', borderUpColor:'#3fb950', borderDownColor:'#f85149', wickUpColor:'#3fb950', wickDownColor:'#f85149' });
      } else if (tipo === "hollow") {
        serie = chart.addCandlestickSeries({ upColor:'transparent', downColor:'#f85149', borderUpColor:'#3fb950', borderDownColor:'#f85149', wickUpColor:'#3fb950', wickDownColor:'#f85149' });
      } else if (tipo === "bars") {
        serie = chart.addBarSeries({ upColor: '#3fb950', downColor: '#f85149' });
      } else if (tipo === "line") {
        serie = chart.addLineSeries({ color: '#3fb950', lineWidth: 2 });
      } else if (tipo === "area") {
        serie = chart.addAreaSeries({ lineColor:'#3fb950', lineWidth:2, topColor:'rgba(63,185,80,0.4)', bottomColor:'rgba(63,185,80,0.0)' });
      } else if (tipo === "heikin") {
        serie = chart.addCandlestickSeries({ upColor:'#3fb950', downColor:'#f85149', borderUpColor:'#3fb950', borderDownColor:'#f85149', wickUpColor:'#3fb950', wickDownColor:'#f85149' });
      }
      if (serie) {
        serie.priceScale().applyOptions({ scaleMargins: { top: 0.08, bottom: 0.22 } });
      }
    }

    crearSerie(tipoActual);

    // ==========================================================================
    // SISTEMA DE DIBUJO INTERACTIVO CON ANCLAJE A TIEMPO Y PRECIO REAL
    // ==========================================================================
    var canvas = document.getElementById('drawing-canvas');
    var ctx = canvas.getContext('2d');
    var activeTool = 'cross';
    var elementosDibujados = [];
    var dibujoEnCurso = null;
    var bloqueado = false;

    function resizeCanvas() {
      var wrap = document.getElementById('chart-wrapper');
      canvas.width = wrap.clientWidth;
      canvas.height = wrap.clientHeight;
      redibujarTodo();
    }
    window.addEventListener('resize', resizeCanvas);
    setTimeout(resizeCanvas, 100);

    // Sincronizar redibujado al hacer zoom o desplazamiento en el gráfico
    chart.timeScale().subscribeVisibleLogicalRangeChange(function(){
      redibujarTodo();
    });

    document.querySelectorAll('.tvtool').forEach(function(btn){
      btn.addEventListener('click', function(){
        var tool = btn.getAttribute('data-tool');
        if (tool === 'clear') {
          elementosDibujados = [];
          redibujarTodo();
          return;
        }
        if (tool === 'lock') {
          bloqueado = !bloqueado;
          btn.style.color = bloqueado ? '#3fb950' : '#8b949e';
          return;
        }

        document.querySelectorAll('.tvtool').forEach(function(b){ 
          if(b.getAttribute('data-tool') !== 'clear' && b.getAttribute('data-tool') !== 'lock') {
            b.classList.remove('active'); 
          }
        });
        
        if(tool !== 'clear' && tool !== 'lock') {
          btn.classList.add('active');
          activeTool = tool;
        }

        if (activeTool === 'cross') {
          canvas.style.pointerEvents = 'none';
          chart.applyOptions({ handleScroll: true, handleScale: true });
        } else {
          canvas.style.pointerEvents = 'auto';
          chart.applyOptions({ handleScroll: false, handleScale: false });
        }
      });
    });

    function redibujarTodo(){
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      elementosDibujados.forEach(function(el){ dibujarElemento(ctx, el); });
      if (dibujoEnCurso) { dibujarElemento(ctx, dibujoEnCurso); }
    }

    function convertirCoord(el){
      // Traduce marcas de tiempo y precios reales a coordenadas de píxeles actuales del canvas
      if (el.tipo === 'hline') {
        var y = serie.priceToCoordinate(el.price);
        return { tipo: 'hline', y: y, price: el.price };
      } else if (el.tipo === 'text') {
        var x = chart.timeScale().timeToCoordinate(el.time);
        var y = serie.priceToCoordinate(el.price);
        return { tipo: 'text', x: x, y: y, texto: el.texto };
      } else {
        var x1 = chart.timeScale().timeToCoordinate(el.time1);
        var y1 = serie.priceToCoordinate(el.price1);
        var x2 = chart.timeScale().timeToCoordinate(el.time2);
        var y2 = serie.priceToCoordinate(el.price2);
        return { tipo: el.tipo, x1: x1, y1: y1, x2: x2, y2: y2, price1: el.price1, price2: el.price2 };
      }
    }

    function dibujarElemento(c, elCrudo){
      var el = convertirCoord(elCrudo);
      if (el.y === null && el.y1 === null) return; // Fuera del área visible actual

      c.save();
      if (el.tipo === 'trend' && el.x1 !== null && el.x2 !== null) {
        c.strokeStyle = '#2962ff';
        c.lineWidth = 2;
        c.beginPath();
        c.moveTo(el.x1, el.y1);
        c.lineTo(el.x2, el.y2);
        c.stroke();
        c.fillStyle = '#2962ff';
        c.fillRect(el.x1 - 3, el.y1 - 3, 6, 6);
        c.fillRect(el.x2 - 3, el.y2 - 3, 6, 6);
      } else if (el.tipo === 'hline' && el.y !== null) {
        c.strokeStyle = '#f5c518';
        c.lineWidth = 1.5;
        c.setLineDash([4, 4]);
        c.beginPath();
        c.moveTo(0, el.y);
        c.lineTo(canvas.width, el.y);
        c.stroke();
        c.fillStyle = '#f5c518';
        c.font = '11px sans-serif';
        c.fillText('Precio: ' + el.price.toFixed(5), 10, el.y - 5);
      } else if (el.tipo === 'fib' && el.x1 !== null && el.x2 !== null) {
        var minY = Math.min(el.y1, el.y2);
        var maxY = Math.max(el.y1, el.y2);
        var altura = maxY - minY;
        var diffPrecios = el.price2 - el.price1;
        var niveles = [
          { val: 0.0, color: '#f85149' },
          { val: 0.236, color: '#ff9800' },
          { val: 0.382, color: '#f5c518' },
          { val: 0.5, color: '#3fb950' },
          { val: 0.618, color: '#58a6ff' },
          { val: 0.786, color: '#a78bfa' },
          { val: 1.0, color: '#f85149' }
        ];
        c.lineWidth = 1;
        niveles.forEach(function(niv){
          var yNiv = minY + (altura * niv.val);
          var precioNiv = el.price1 + (diffPrecios * niv.val);
          c.strokeStyle = niv.color;
          c.fillStyle = niv.color;
          c.beginPath();
          c.moveTo(el.x1, yNiv);
          c.lineTo(el.x2, yNiv);
          c.stroke();
          c.font = '11px sans-serif';
          c.fillText((niv.val * 100).toFixed(1) + '% (' + precioNiv.toFixed(4) + ')', Math.min(el.x1, el.x2) + 5, yNiv - 3);
        });
      } else if (el.tipo === 'text' && el.x !== null) {
        c.fillStyle = '#ffffff';
        c.font = '13px sans-serif';
        c.fillText(el.texto || 'Texto', el.x, el.y);
      } else if (el.tipo === 'measure' && el.x1 !== null && el.x2 !== null) {
        c.strokeStyle = '#a78bfa';
        c.fillStyle = 'rgba(167, 139, 250, 0.15)';
        c.lineWidth = 1;
        c.setLineDash([2, 2]);
        var w = el.x2 - el.x1;
        var h = el.y2 - el.y1;
        c.fillRect(el.x1, el.y1, w, h);
        c.strokeRect(el.x1, el.y1, w, h);
        
        var barsDiff = Math.abs(Math.round((el.x2 - el.x1) / 10));
        var pipsDiff = ((el.price2 - el.price1) * 10000).toFixed(1);
        c.fillStyle = '#a78bfa';
        c.font = '11px monospace';
        c.fillText('ΔP: ' + pipsDiff + ' pips | ' + barsDiff + ' barras', el.x1 + 6, el.y1 + 16);
      }
      c.restore();
    }

    var isDrawing = false;
    var startX, startY, startTime, startPrice;

    canvas.addEventListener('mousedown', function(e){
      if (activeTool === 'cross' || bloqueado) return;
      var rect = canvas.getBoundingClientRect();
      startX = e.clientX - rect.left;
      startY = e.clientY - rect.top;
      
      startTime = chart.timeScale().coordinateToTime(startX);
      startPrice = serie.coordinateToPrice(startY);

      if (!startTime || startPrice === null) return;
      isDrawing = true;

      if (activeTool === 'text') {
        var textoPrompt = prompt("Introduce el texto analítico:", "Soporte Clave / Estructura");
        if (textoPrompt) {
          elementosDibujados.push({ tipo: 'text', time: startTime, price: startPrice, texto: textoPrompt });
          redibujarTodo();
        }
        isDrawing = false;
        document.getElementById('tool-cross').click();
      } else if (activeTool === 'hline') {
        elementosDibujados.push({ tipo: 'hline', price: startPrice });
        redibujarTodo();
        isDrawing = false;
        document.getElementById('tool-cross').click();
      }
    });

    canvas.addEventListener('mousemove', function(e){
      if (!isDrawing || bloqueado) return;
      var rect = canvas.getBoundingClientRect();
      var currentX = e.clientX - rect.left;
      var currentY = e.clientY - rect.top;
      
      var currentTime = chart.timeScale().coordinateToTime(currentX);
      var currentPrice = serie.coordinateToPrice(currentY);
      if (!currentTime || currentPrice === null) return;

      if (activeTool === 'trend') {
        dibujoEnCurso = { tipo: 'trend', time1: startTime, price1: startPrice, time2: currentTime, price2: currentPrice };
      } else if (activeTool === 'fib') {
        dibujoEnCurso = { tipo: 'fib', time1: startTime, price1: startPrice, time2: currentTime, price2: currentPrice };
      } else if (activeTool === 'measure') {
        dibujoEnCurso = { tipo: 'measure', time1: startTime, price1: startPrice, time2: currentTime, price2: currentPrice };
      }
      redibujarTodo();
    });

    canvas.addEventListener('mouseup', function(e){
      if (!isDrawing || bloqueado) return;
      isDrawing = false;
      if (dibujoEnCurso) {
        elementosDibujados.push(dibujoEnCurso);
        dibujoEnCurso = null;
        redibujarTodo();
      }
      document.getElementById('tool-cross').click();
    });

    // ==========================================================================
    // CÁLCULOS MATEMÁTICOS DE INDICADORES TÉCNICOS
    // ==========================================================================
    function calcularSMA(datos, periodo){
      var out = [];
      for (var i = periodo - 1; i < datos.length; i++){
        var suma = 0;
        for (var j = i - periodo + 1; j <= i; j++){ suma += datos[j].close; }
        out.push({ time: datos[i].time, value: suma / periodo });
      }
      return out;
    }

    function calcularEMA(datos, periodo){
      var out = [];
      var multiplicador = 2 / (periodo + 1);
      var emaPrevio = 0;
      for (var i = 0; i < datos.length; i++){
        if (i < periodo - 1) continue;
        if (i === periodo - 1) {
          var suma = 0;
          for (var j = 0; j <= i; j++) suma += datos[j].close;
          emaPrevio = suma / periodo;
          out.push({ time: datos[i].time, value: emaPrevio });
        } else {
          emaPrevio = (datos[i].close - emaPrevio) * multiplicador + emaPrevio;
          out.push({ time: datos[i].time, value: emaPrevio });
        }
      }
      return out;
    }

    function calcularBollinger(datos, periodo, desviaciones){
      var sma = calcularSMA(datos, periodo);
      var superiores = [];
      var inferiores = [];
      var medias = [];
      
      for (var i = 0; i < sma.length; i++){
        var idxDatos = i + periodo - 1;
        var sumaCuadrados = 0;
        var mediaVal = sma[i].value;
        for (var j = idxDatos - periodo + 1; j <= idxDatos; j++){
          var diff = datos[j].close - mediaVal;
          sumaCuadrados += diff * diff;
        }
        var desviacionEst = Math.sqrt(sumaCuadrados / periodo);
        var tiempo = sma[i].time;
        medias.push({ time: tiempo, value: mediaVal });
        superiores.push({ time: tiempo, value: mediaVal + (desviaciones * desviacionEst) });
        inferiores.push({ time: tiempo, value: mediaVal - (desviaciones * desviacionEst) });
      }
      return { medias: medias, superiores: superiores, inferiores: inferiores };
    }

    function calcularRSI(datos, periodo){
      var out = [];
      var ganancias = 0, perdidas = 0;
      for (var i = 1; i <= periodo; i++){
        var cambio = datos[i].close - datos[i-1].close;
        if (cambio >= 0) ganancias += cambio;
        else perdidas -= cambio;
      }
      var mediaGanancia = ganancias / periodo;
      var mediaPerdida = perdidas / periodo;
      
      for (var i = periodo + 1; i < datos.length; i++){
        var cambio = datos[i].close - datos[i-1].close;
        var g = cambio >= 0 ? cambio : 0;
        var p = cambio < 0 ? -cambio : 0;
        mediaGanancia = (mediaGanancia * (periodo - 1) + g) / periodo;
        mediaPerdida = (mediaPerdida * (periodo - 1) + p) / periodo;
        
        var rs = mediaPerdida === 0 ? 100 : mediaGanancia / mediaPerdida;
        var rsiVal = 100 - (100 / (1 + rs));
        out.push({ time: datos[i].time, value: rsiVal });
      }
      return out;
    }

    function inicializarRSIChart(){
      if (chartRsi) return;
      var rsiEl = document.getElementById('rsi-container');
      rsiEl.style.display = 'block';
      chartRsi = LightweightCharts.createChart(rsiEl, {
        autoSize: true,
        layout: { background: { color: '#0d1117' }, textColor: '#d1d4dc', fontSize: 11 },
        grid: { vertLines: { color: '#161b22' }, horzLines: { color: '#161b22' } },
        timeScale: { visible: false },
        rightPriceScale: { borderColor: '#30363d', scaleMargins: { top: 0.1, bottom: 0.1 } }
      });
      serieRsi = chartRsi.addLineSeries({ color: '#a78bfa', lineWidth: 2 });
      
      chart.timeScale().subscribeVisibleLogicalRangeChange(function(range){
        if (chartRsi) chartRsi.timeScale().setVisibleLogicalRange(range);
      });
    }

    function actualizarIndicadoresActivos(){
      if (indicadores.sma20) {
        if (!seriesInd.sma20) seriesInd.sma20 = chart.addLineSeries({ color: '#f5c518', lineWidth: 2, priceLineVisible: false });
        seriesInd.sma20.setData(calcularSMA(datosActuales, 20));
      } else if (seriesInd.sma20) {
        chart.removeSeries(seriesInd.sma20); seriesInd.sma20 = null;
      }

      if (indicadores.sma50) {
        if (!seriesInd.sma50) seriesInd.sma50 = chart.addLineSeries({ color: '#3399ff', lineWidth: 2, priceLineVisible: false });
        seriesInd.sma50.setData(calcularSMA(datosActuales, 50));
      } else if (seriesInd.sma50) {
        chart.removeSeries(seriesInd.sma50); seriesInd.sma50 = null;
      }

      if (indicadores.ema20) {
        if (!seriesInd.ema20) seriesInd.ema20 = chart.addLineSeries({ color: '#ff6600', lineWidth: 2, priceLineVisible: false });
        seriesInd.ema20.setData(calcularEMA(datosActuales, 20));
      } else if (seriesInd.ema20) {
        chart.removeSeries(seriesInd.ema20); seriesInd.ema20 = null;
      }

      if (indicadores.bollinger) {
        var bb = calcularBollinger(datosActuales, 20, 2);
        if (!seriesInd.bolpsuper) {
          seriesInd.bolpsuper = chart.addLineSeries({ color: 'rgba(41, 98, 255, 0.7)', lineWidth: 1, priceLineVisible: false });
          seriesInd.bolpmedia = chart.addLineSeries({ color: 'rgba(255, 152, 0, 0.7)', lineWidth: 1, priceLineVisible: false });
          seriesInd.bolpsuper.setData(bb.superiores);
          seriesInd.bolpmedia.setData(bb.medias);
        } else {
          seriesInd.bolpsuper.setData(bb.superiores);
          seriesInd.bolpmedia.setData(bb.medias);
        }
      } else if (seriesInd.bolpsuper) {
        chart.removeSeries(seriesInd.bolpsuper); seriesInd.bolpsuper = null;
        chart.removeSeries(seriesInd.bolpmedia); seriesInd.bolpmedia = null;
      }

      if (indicadores.rsi) {
        inicializarRSIChart();
        if (serieRsi) serieRsi.setData(calcularRSI(datosActuales, 14));
      } else {
        var rsiEl = document.getElementById('rsi-container');
        rsiEl.style.display = 'none';
        if (chartRsi) { chartRsi.remove(); chartRsi = null; serieRsi = null; }
      }
    }

    function calcularHeikinAshi(datos){
      var ha = [];
      for (var i = 0; i < datos.length; i++){
        var d = datos[i];
        var haClose = (d.open + d.high + d.low + d.close) / 4;
        var haOpen = (i === 0) ? (d.open + d.close) / 2 : (ha[i-1].open + ha[i-1].close) / 2;
        var haHigh = Math.max(d.high, haOpen, haClose);
        var haLow = Math.min(d.low, haOpen, haClose);
        ha.push({ time: d.time, open: haOpen, high: haHigh, low: haLow, close: haClose, volume: d.volume });
      }
      return ha;
    }

    function formatearDatos(datos, tipo){
      if (tipo === "line" || tipo === "area") {
        return datos.map(function(v){ return { time: v.time, value: v.close }; });
      }
      if (tipo === "heikin") {
        var ha = calcularHeikinAshi(datos);
        return ha.map(function(v){ return { time: v.time, open: v.open, high: v.high, low: v.low, close: v.close }; });
      }
      return datos.map(function(v){ return { time: v.time, open: v.open, high: v.high, low: v.low, close: v.close }; });
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

    function cargar(tf, n, ajustarFit){
      tfActual = tf;
      nBarrasActual = n;
      fetch(API + "/velas/" + encodeURIComponent(SIMBOLO) + "?tf=" + tf + "&n=" + n)
        .then(function(r){ return r.json(); })
        .then(function(velas){
          if (velas && velas.length){
            datosActuales = velas;
            serie.setData(formatearDatos(velas, tipoActual));
            serieVolumen.setData(velas.map(aPuntoVolumen));
            if (ajustarFit) { chart.timeScale().fitContent(); }
            actualizarLeyenda(velas[velas.length - 1]);
            actualizarIndicadoresActivos();
            redibujarTodo();
          }
        })
        .catch(function(){});
    }

    cargar(tfActual, nBarrasActual, true);

    var btnTypeSelect = document.getElementById('btn-type-select');
    var typeMenu = document.getElementById('type-menu');
    var btnIndSelect = document.getElementById('btn-ind-select');
    var indMenu = document.getElementById('ind-menu');

    btnTypeSelect.addEventListener('click', function(e){ e.stopPropagation(); typeMenu.classList.toggle('show'); indMenu.classList.remove('show'); });
    btnIndSelect.addEventListener('click', function(e){ e.stopPropagation(); indMenu.classList.toggle('show'); typeMenu.classList.remove('show'); });

    window.addEventListener('click', function(){
      typeMenu.classList.remove('show');
      indMenu.classList.remove('show');
    });

    document.querySelectorAll('#type-menu .tv-drop-item').forEach(function(item){
      item.addEventListener('click', function(){
        tipoActual = item.getAttribute('data-type');
        btnTypeSelect.innerHTML = item.innerText + ' ▾';
        crearSerie(tipoActual);
        if (datosActuales.length){
          serie.setData(formatearDatos(datosActuales, tipoActual));
          serieVolumen.setData(datosActuales.map(aPuntoVolumen));
          actualizarIndicadoresActivos();
        }
      });
    });

    document.querySelectorAll('#ind-menu .tv-drop-item').forEach(function(item){
      item.addEventListener('click', function(){
        var indKey = item.getAttribute('data-ind');
        indicadores[indKey] = !indicadores[indKey];
        var stSpan = document.getElementById('st-' + indKey);
        if (indicadores[indKey]) {
          item.classList.add('active-ind');
          stSpan.innerText = 'On';
        } else {
          item.classList.remove('active-ind');
          stSpan.innerText = 'Off';
        }
        actualizarIndicadoresActivos();
      });
    });

    setInterval(function(){
      fetch(API + "/ultima/" + encodeURIComponent(SIMBOLO) + "?tf=" + tfActual)
        .then(function(r){ return r.json(); })
        .then(function(v){
          if (v && v.time){
            if (datosActuales.length && datosActuales[datosActuales.length - 1].time === v.time){
              datosActuales[datosActuales.length - 1] = v;
            } else {
              datosActuales.push(v);
            }
            var datosFormateados = formatearDatos(datosActuales, tipoActual);
            serie.update(datosFormateados[datosFormateados.length - 1]);
            serieVolumen.update(aPuntoVolumen(v));
            actualizarLeyenda(v);
            actualizarIndicadoresActivos();
            redibujarTodo();
          }
        })
        .catch(function(){});
    }, 1500);

    chart.subscribeCrosshairMove(function(param){
      if (!param || !param.time){
        if (datosActuales.length) actualizarLeyenda(datosActuales[datosActuales.length - 1]);
        return;
      }
      var idx = datosActuales.findIndex(function(d){ return d.time === param.time; });
      if (idx >= 0) actualizarLeyenda(datosActuales[idx]);
    });

    document.querySelectorAll('.tvrange').forEach(function(btn){
      btn.addEventListener('click', function(){
        document.querySelectorAll('.tvrange').forEach(function(b){ b.classList.remove('active'); });
        btn.classList.add('active');
        cargar(btn.getAttribute('data-tf'), parseInt(btn.getAttribute('data-n'), 10), true);
      });
    });

    var btnShot = document.getElementById('btn-shot');
    if (btnShot){
      btnShot.addEventListener('click', function(){
        try {
          var canvasScreenshot = chart.takeScreenshot();
          var enlace = document.createElement('a');
          enlace.download = SIMBOLO + '_indicadores.png';
          enlace.href = canvasScreenshot.toDataURL();
          enlace.click();
        } catch (e) {}
      });
    }

    var btnFull = document.getElementById('btn-full');
    var wrap = document.getElementById('tv-wrap');
    if (btnFull && wrap){
      btnFull.addEventListener('click', function(){
        if (!document.fullscreenElement){
          if (wrap.requestFullscreen) wrap.requestFullscreen();
        } else {
          if (document.exitFullscreen) document.exitFullscreen();
        }
      });
    }
  }
  iniciar();
})();
</script>
"""

def renderizar_panel_central(main: Optional[ModuleType]):
    inicializar_mt5()

    activo_actual = st.session_state.get("activo_seleccionado", "EURUSD...")
    activo_visible = activo_actual.replace("...", "").strip()
    # Nombre REAL en este terminal (con o sin "..."): funciona en el MT5 de Emilio
    # (EURUSD...) y en el de Cristian (EURUSD). Se usa para pedir precio/gráfico.
    simbolo_api = resolver_simbolo(activo_actual)

    @st.fragment(run_every="2s")
    def _cabecera_precio():
        info_tick = obtener_precio_actual(activo_visible)
        if "error" not in info_tick:
            precio_actual = info_tick.get("last", 0) if info_tick.get("last", 0) > 0 else info_tick.get("bid", 0)
        else:
            precio_actual = 0.0
        
        clave = f"_prev_precio_{activo_visible}"
        anterior = st.session_state.get(clave, precio_actual)
        sube_activo = precio_actual >= anterior
        st.session_state[clave] = precio_actual
        color_var_activo = "#3fb950" if sube_activo else "#f85149"
        bid = float(info_tick.get("bid", 0))
        ask = float(info_tick.get("ask", 0))
        
        st.markdown(f"""
            <div style='background-color: #161b22; padding: 10px 16px; border-radius: 8px; border: 1px solid #30363d; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;'>
                <div style='display: flex; align-items: center; gap: 14px;'>
                    <span style='font-size: 20px; font-weight: bold; color: #ffffff;'>{activo_visible}</span>
                    <span style='background: #30363d; color: #8b949e; padding: 2px 8px; border-radius: 4px; font-size: 11px;'>XM / MT5</span>
                    <span style='font-size: 22px; font-weight: bold; font-family: monospace; color: {color_var_activo};'>${precio_actual:,.5f}</span>
                    <span style='font-size: 14px; font-weight: 600; color: {color_var_activo};'>Bid: {bid:,.5f} | Ask: {ask:,.5f}</span>
                </div>
                <div style='font-size: 13px; color: #8b949e; font-weight: 600; display: flex; align-items: center; gap: 6px;'>
                    Conectado <span style='color: #3fb950; font-size: 16px;'>●</span>
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
        .replace("__SIMBOLO_API__", simbolo_api)     # nombre real del terminal (con/sin '...')
        .replace("__SIMBOLO__", activo_visible)       # nombre limpio solo para mostrar en la leyenda
        .replace("__TF__", temporalidad_elegida)
        .replace("__TIPO__", tipo_grafico)
    )
    components.html(html_chart, height=600)

    # --- ZONA DE CHAT INFERIOR CONECTADA A main.py ---
    st.markdown("---")
    st.markdown("### 🤖 Asistente IA Analítico (Consola, Gráficos e Imágenes)")
    st.caption("Interactúa libremente con el agente bursátil. Mantiene contexto, herramientas, gráficos e imágenes renderizadas.")

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
                        activo_encontrado = activo_visible

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