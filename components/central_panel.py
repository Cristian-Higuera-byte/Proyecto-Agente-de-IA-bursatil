import json
import os
import time
from html import escape
from types import ModuleType
from typing import Optional, Tuple

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
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
)

# URL de la API que sirve las velas al gráfico (/velas y /ultima).
API_URL = os.environ.get("MT5_API_URL", "http://localhost:8000")

# ==========================================================================
# Plantilla HTML del gráfico con Línea de Tendencia Interactiva Avanzada
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
    #tv-tf { display:flex; align-items:center; gap:2px; font-family:-apple-system,"Segoe UI",Roboto,Arial,sans-serif; }
    .tvtf {
        background:transparent; border:1px solid transparent; color:#8b949e; font-size:12px;
        font-weight:600; padding:5px 8px; border-radius:6px; cursor:pointer; white-space:nowrap;
        transition: background .15s ease, color .15s ease, border-color .15s ease;
    }
    .tvtf:hover { background:rgba(255,255,255,0.08); color:#ffffff; }
    .tvtf.active { background:rgba(88,166,255,0.18); color:#58a6ff; border-color:rgba(88,166,255,0.3); }
    .tv-rangelabel { color:#6e7681; font-size:12px; font-weight:600; padding:0 8px 0 2px; white-space:nowrap; }
</style>

<div id="tv-wrap">
    <div id="tv-topbar">
        <div id="tv-legend">
            <span class="tv-sym">__SIMBOLO_HTML__</span>
            <span class="tv-ohlc" id="tv-ohlc-vals">Cargando…</span>
            <span class="tv-vol" id="tv-vol-val"></span>
        </div>
            <div id="tv-tf" title="Temporalidad">
            <button class="tvtf" data-tf="M1" data-n="1500">M1</button>
            <button class="tvtf" data-tf="M5" data-n="1500">M5</button>
            <button class="tvtf" data-tf="M15" data-n="1500">M15</button>
            <button class="tvtf" data-tf="M30" data-n="1500">M30</button>
            <button class="tvtf active" data-tf="H1" data-n="1500">H1</button>
            <button class="tvtf" data-tf="H4" data-n="1500">H4</button>
            <button class="tvtf" data-tf="D1" data-n="1000">D1</button>
            <button class="tvtf" data-tf="W1" data-n="520">W1</button>
            <button class="tvtf" data-tf="MN1" data-n="180">MN</button>
        </div>
        <div id="tv-actions">
            <!-- Selector Tipo de Gráfico -->
            <div class="tv-dropdown" id="type-dropdown">
                <button class="tvbtn activo" id="btn-type-select" title="Cambiar tipo de gráfico">🕯 Velas ▾</button>
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
        <span class="tv-rangelabel">Rango</span>
        <button class="tvrange" data-tf="M5" data-n="288">1D</button>
        <button class="tvrange" data-tf="M15" data-n="480">5D</button>
        <button class="tvrange" data-tf="H1" data-n="528">1 mes</button>
        <button class="tvrange" data-tf="H4" data-n="400">3 meses</button>
        <button class="tvrange" data-tf="D1" data-n="132">6 meses</button>
        <button class="tvrange" data-tf="D1" data-n="252">1 año</button>
        <button class="tvrange" data-tf="W1" data-n="260">5 años</button>
        <button class="tvrange" data-tf="W1" data-n="2000">Todo</button>
    </div>
</div>
<script>
window.onerror = function(msg, src, line){
  var e = document.getElementById('tv-ohlc-vals');
  if (e) e.innerText = 'Error JS: ' + msg + ' (línea ' + line + ')';
};
setTimeout(function(){
  var e = document.getElementById('tv-ohlc-vals');
  if (!window.LightweightCharts && e) e.innerText = 'No cargó lightweight-charts (CDN bloqueado o sin internet)';
}, 4000);
</script>

<script src="https://cdn.jsdelivr.net/npm/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<script>
(function(){
  var API = __API_URL_JS__;
  var SIMBOLO = __SIMBOLO_JS__;
  var DIGITS = __DIGITS__;
  var PIP = __PIP__;

  var PF = { type: 'price', precision: DIGITS, minMove: Math.pow(10, -DIGITS) };

  var tfActual = "H1";
  var nBarrasActual = 1500;
  var tipoActual = "candlestick";
  var datosActuales = [];

  var cargaId = 0;
  var cargando = false;
  var pollEnCurso = false;

  var indicadores = { sma20: false, sma50: false, ema20: false, bollinger: false, rsi: false };
  var seriesInd = { sma20: null, sma50: null, ema20: null, bolsuper: null, bolmedia: null, bolinf: null };

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
      rightPriceScale: { borderColor: '#30363d', minimumWidth: 72 },
      crosshair: { mode: 0 }
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
        serie = chart.addCandlestickSeries({ priceFormat: PF, upColor:'#3fb950', downColor:'#f85149', borderUpColor:'#3fb950', borderDownColor:'#f85149', wickUpColor:'#3fb950', wickDownColor:'#f85149' });
      } else if (tipo === "hollow") {
        serie = chart.addCandlestickSeries({ priceFormat: PF, upColor:'transparent', downColor:'#f85149', borderUpColor:'#3fb950', borderDownColor:'#f85149', wickUpColor:'#3fb950', wickDownColor:'#f85149' });
      } else if (tipo === "bars") {
        serie = chart.addBarSeries({ priceFormat: PF, upColor: '#3fb950', downColor: '#f85149' });
      } else if (tipo === "line") {
        serie = chart.addLineSeries({ priceFormat: PF, color: '#3fb950', lineWidth: 2 });
      } else if (tipo === "area") {
        serie = chart.addAreaSeries({ priceFormat: PF, lineColor:'#3fb950', lineWidth:2, topColor:'rgba(63,185,80,0.4)', bottomColor:'rgba(63,185,80,0.0)' });
      } else if (tipo === "heikin") {
        serie = chart.addCandlestickSeries({ priceFormat: PF, upColor:'#3fb950', downColor:'#f85149', borderUpColor:'#3fb950', borderDownColor:'#f85149', wickUpColor:'#3fb950', wickDownColor:'#f85149' });
      }
      if (serie) {
        serie.priceScale().applyOptions({ scaleMargins: { top: 0.08, bottom: 0.22 } });
      }
    }

    crearSerie(tipoActual);

    // ==========================================================================
    // SISTEMA DE DIBUJO PROFESIONAL (objetos editables, imán, deshacer, sin bloquear el gráfico)
    // ==========================================================================
    var canvas = document.getElementById('drawing-canvas');
    var ctx = canvas.getContext('2d');
    var wrapEl = document.getElementById('chart-wrapper');
    var activeTool = 'cross';
    var bloqueado = false;
    var imanActivo = true;           // Imán a OHLC (Ctrl lo invierte temporalmente, como TradingView)

    var seleccionadoId = null;       // Índice del dibujo seleccionado
    var hoverId = null;              // Índice del dibujo bajo el cursor
    var dibujoEnCurso = null;        // Dibujo que se está creando
    var esperandoSegundoClick = false;
    var inicioClick = null;          // Posición (px) donde empezó el dibujo actual
    var arrastre = null;             // Edición en curso: mover dibujo o extremo

    var NIVELES_FIB = [
      { val: 0.0,   color: '#f85149' }, { val: 0.236, color: '#ff9800' },
      { val: 0.382, color: '#f5c518' }, { val: 0.5,   color: '#3fb950' },
      { val: 0.618, color: '#58a6ff' }, { val: 0.786, color: '#a78bfa' },
      { val: 1.0,   color: '#f85149' }
    ];

    // Cursores (la clase fuerza el cursor sobre los canvas internos del gráfico)
    var estiloCursor = document.createElement('style');
    estiloCursor.textContent =
      '#chart-wrapper.cur-mover, #chart-wrapper.cur-mover * { cursor: move !important; }' +
      '#chart-wrapper.cur-punto, #chart-wrapper.cur-punto * { cursor: pointer !important; }' +
      '#chart-wrapper.cur-dibujar, #chart-wrapper.cur-dibujar * { cursor: crosshair !important; }';
    document.head.appendChild(estiloCursor);
    function setCursor(cls){
      wrapEl.classList.remove('cur-mover', 'cur-punto', 'cur-dibujar');
      if (cls) wrapEl.classList.add(cls);
    }

    // --- Persistencia + historial (deshacer / rehacer) ---
    var storageKey = 'dibujos_' + SIMBOLO;
    var elementosDibujados = [];
    try {
      var guardados = localStorage.getItem(storageKey);
      if (guardados) { elementosDibujados = JSON.parse(guardados); }
    } catch(e) { elementosDibujados = []; }

    var historial = [JSON.stringify(elementosDibujados)];
    var posHist = 0;

    function guardarDibujosLocal() {
      try { localStorage.setItem(storageKey, JSON.stringify(elementosDibujados)); } catch(e) {}
    }
    function confirmarCambio(){
      historial = historial.slice(0, posHist + 1);
      historial.push(JSON.stringify(elementosDibujados));
      if (historial.length > 60) historial.shift();
      posHist = historial.length - 1;
      guardarDibujosLocal();
      redibujarTodo();
    }
    function restaurarHistorial(){
      elementosDibujados = JSON.parse(historial[posHist]);
      seleccionadoId = null; hoverId = null;
      guardarDibujosLocal();
      redibujarTodo();
    }
    function deshacer(){ if (posHist > 0) { posHist--; restaurarHistorial(); } }
    function rehacer(){ if (posHist < historial.length - 1) { posHist++; restaurarHistorial(); } }

    // --- Canvas ---
    var cssW = 0, cssH = 0;
    var sucio = true;

    function redibujarTodo(){ sucio = true; }

    function resizeCanvas() {
      var dpr = window.devicePixelRatio || 1;
      cssW = wrapEl.clientWidth;
      cssH = wrapEl.clientHeight;
      canvas.width = Math.max(1, Math.round(cssW * dpr));
      canvas.height = Math.max(1, Math.round(cssH * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      redibujarTodo();
    }

    if (window.ResizeObserver) {
      new ResizeObserver(resizeCanvas).observe(wrapEl);
    } else {
      window.addEventListener('resize', resizeCanvas);
    }
    resizeCanvas();

    function areaTrazado(){
      var anchoEje = 60, altoEje = 28;
      try { anchoEje = chart.priceScale('right').width(); } catch (e) {}
      try { altoEje = chart.timeScale().height(); } catch (e) {}
      return { w: Math.max(0, cssW - anchoEje), h: Math.max(0, cssH - altoEje) };
    }

    chart.timeScale().subscribeVisibleLogicalRangeChange(function(range){
      redibujarTodo();
      if (chartRsi && range) chartRsi.timeScale().setVisibleLogicalRange(range);
    });

    function ok(){
      for (var i = 0; i < arguments.length; i++){
        var v = arguments[i];
        if (v === null || v === undefined || typeof v !== 'number' || !isFinite(v)) return false;
      }
      return true;
    }

    // --- Conversión tiempo <-> posición (permite dibujar más allá de las velas cargadas) ---
    // Nota: asume que "time" de la API es un timestamp UNIX en segundos (como ya lo usa tu gráfico).
    var cacheSeg = { n: -1, t: -1, v: 60 };
    function segBarra(){
      var n = datosActuales.length;
      if (n < 2) return 60;
      var tUlt = datosActuales[n - 1].time;
      if (cacheSeg.n === n && cacheSeg.t === tUlt) return cacheSeg.v;
      var difs = [];
      for (var i = Math.max(1, n - 60); i < n; i++){
        var d = datosActuales[i].time - datosActuales[i - 1].time;
        if (d > 0) difs.push(d);
      }
      difs.sort(function(a, b){ return a - b; });
      cacheSeg = { n: n, t: tUlt, v: difs.length ? difs[Math.floor(difs.length / 2)] : 60 };
      return cacheSeg.v;
    }

    function tiempoALogico(t){
      var n = datosActuales.length;
      if (!n || typeof t !== 'number' || !isFinite(t)) return null;
      var seg = segBarra();
      var primero = datosActuales[0].time, ultimo = datosActuales[n - 1].time;
      if (t <= primero) return (t - primero) / seg;
      if (t >= ultimo) return (n - 1) + (t - ultimo) / seg;
      var lo = 0, hi = n - 1;
      while (hi - lo > 1){
        var mid = (lo + hi) >> 1;
        if (datosActuales[mid].time <= t) lo = mid; else hi = mid;
      }
      var t0 = datosActuales[lo].time, t1 = datosActuales[hi].time;
      return lo + (t - t0) / (t1 - t0);
    }

    function logicoATiempo(l){
      var n = datosActuales.length;
      if (!n || typeof l !== 'number' || !isFinite(l)) return null;
      var seg = segBarra();
      if (l <= 0) return datosActuales[0].time + l * seg;
      if (l >= n - 1) return datosActuales[n - 1].time + (l - (n - 1)) * seg;
      var i = Math.floor(l);
      var t0 = datosActuales[i].time, t1 = datosActuales[i + 1].time;
      return t0 + (l - i) * (t1 - t0);
    }

    function xDeTiempo(t){
      var l = tiempoALogico(t);
      if (l === null) return null;
      return chart.timeScale().logicalToCoordinate(l);
    }
    function yDePrecio(p){
      if (!serie || typeof p !== 'number') return null;
      return serie.priceToCoordinate(p);
    }

    function magnetEfectivo(e){ return imanActivo !== !!(e && e.ctrlKey); }

    // Convierte una posición del mouse en un punto {l, time, price}, con imán opcional a OHLC
    function puntoDesdeMouse(x, y, conIman){
      if (!serie || !datosActuales.length) return null;
      var l = chart.timeScale().coordinateToLogical(x);
      var p = serie.coordinateToPrice(y);
      if (l === null || p === null) return null;
      if (conIman){
        var i = Math.round(l);
        if (i >= 0 && i < datosActuales.length){
          var v = datosActuales[i];
          var mejor = null, mejorD = 14;
          [v.open, v.high, v.low, v.close].forEach(function(cand){
            var cy = serie.priceToCoordinate(cand);
            if (cy !== null){
              var d = Math.abs(cy - y);
              if (d < mejorD){ mejorD = d; mejor = cand; }
            }
          });
          l = i;
          if (mejor !== null) p = mejor;
        }
      }
      var t = logicoATiempo(l);
      if (t === null) return null;
      return { l: l, time: t, price: p };
    }

    // --- Geometría y detección de clics (hit-test) ---
    function geom(el){
      if (el.tipo === 'hline') return { y: yDePrecio(el.price) };
      if (el.tipo === 'text') return { x: xDeTiempo(el.time), y: yDePrecio(el.price) };
      return { x1: xDeTiempo(el.time1), y1: yDePrecio(el.price1), x2: xDeTiempo(el.time2), y2: yDePrecio(el.price2) };
    }

    function distSeg(px, py, x1, y1, x2, y2){
      var dx = x2 - x1, dy = y2 - y1;
      var l2 = dx * dx + dy * dy;
      var t = l2 ? ((px - x1) * dx + (py - y1) * dy) / l2 : 0;
      t = Math.max(0, Math.min(1, t));
      return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy));
    }

    // Devuelve null, 'p1', 'p2' o 'body'
    function hitTest(el, x, y, seleccionado){
      var g = geom(el);
      if (el.tipo === 'hline') return (ok(g.y) && Math.abs(y - g.y) <= 6) ? 'body' : null;
      if (el.tipo === 'text'){
        if (!ok(g.x, g.y)) return null;
        ctx.font = '13px sans-serif';
        var w = ctx.measureText(el.texto || 'Texto').width;
        return (x >= g.x - 4 && x <= g.x + w + 4 && y >= g.y - 16 && y <= g.y + 6) ? 'body' : null;
      }
      if (!ok(g.x1, g.y1, g.x2, g.y2)) return null;
      if (seleccionado){
        if (Math.hypot(x - g.x1, y - g.y1) <= 10) return 'p1';
        if (Math.hypot(x - g.x2, y - g.y2) <= 10) return 'p2';
      }
      if (el.tipo === 'trend') return distSeg(x, y, g.x1, g.y1, g.x2, g.y2) <= 6 ? 'body' : null;
      var xa = Math.min(g.x1, g.x2), xb = Math.max(g.x1, g.x2);
      var ya = Math.min(g.y1, g.y2), yb = Math.max(g.y1, g.y2);
      if (el.tipo === 'measure'){
        return (x >= xa - 4 && x <= xb + 4 && y >= ya - 4 && y <= yb + 4) ? 'body' : null;
      }
      if (el.tipo === 'fib'){
        if (x < xa - 6 || x > xb + 6) return null;
        for (var i = 0; i < NIVELES_FIB.length; i++){
          var yn = g.y1 + (g.y2 - g.y1) * NIVELES_FIB[i].val;
          if (Math.abs(y - yn) <= 6) return 'body';
        }
        return distSeg(x, y, g.x1, g.y1, g.x2, g.y2) <= 6 ? 'body' : null;
      }
      return null;
    }

    function elementoBajo(x, y){
      if (seleccionadoId !== null && elementosDibujados[seleccionadoId]){
        var h = hitTest(elementosDibujados[seleccionadoId], x, y, true);
        if (h) return { idx: seleccionadoId, parte: h };
      }
      for (var i = elementosDibujados.length - 1; i >= 0; i--){
        var h2 = hitTest(elementosDibujados[i], x, y, false);
        if (h2) return { idx: i, parte: h2 };
      }
      return null;
    }

    // --- Render ---
    function dibujarHandle(c, x, y, col){
      c.save();
      c.fillStyle = '#ffffff'; c.strokeStyle = col; c.lineWidth = 2;
      c.beginPath(); c.arc(x, y, 5, 0, 2 * Math.PI); c.fill(); c.stroke();
      c.restore();
    }

    function dibujarElemento(c, el, sel, hov){
      var g = geom(el);
      c.save();
      if (el.tipo === 'trend' && ok(g.x1, g.y1, g.x2, g.y2)) {
        var col = el.color || '#2962ff';
        c.strokeStyle = col;
        c.lineWidth = (el.ancho || 2) + ((hov && !sel) ? 1 : 0);
        c.lineCap = 'round';
        c.beginPath(); c.moveTo(g.x1, g.y1); c.lineTo(g.x2, g.y2); c.stroke();
        if (sel) { dibujarHandle(c, g.x1, g.y1, col); dibujarHandle(c, g.x2, g.y2, col); }

      } else if (el.tipo === 'hline' && ok(g.y)) {
        var colH = el.color || '#f5c518';
        c.strokeStyle = colH;
        c.lineWidth = (el.ancho || 1.5) + ((hov && !sel) ? 1 : 0);
        c.setLineDash([6, 4]);
        c.beginPath(); c.moveTo(0, g.y); c.lineTo(cssW, g.y); c.stroke();
        c.setLineDash([]);
        if (sel) dibujarHandle(c, areaTrazado().w * 0.5, g.y, colH);

      } else if (el.tipo === 'fib' && ok(g.x1, g.y1, g.x2, g.y2)) {
        var xa = Math.min(g.x1, g.x2), xb = Math.max(g.x1, g.x2);
        var dY = g.y2 - g.y1, dP = el.price2 - el.price1;
        var nv = NIVELES_FIB.map(function(n){
          return { n: n, y: g.y1 + dY * n.val, precio: el.price1 + dP * n.val };
        });
        c.globalAlpha = 0.07;
        for (var i = 0; i < nv.length - 1; i++){
          c.fillStyle = nv[i + 1].n.color;
          c.fillRect(xa, Math.min(nv[i].y, nv[i + 1].y), xb - xa, Math.abs(nv[i + 1].y - nv[i].y));
        }
        c.globalAlpha = 1;
        c.lineWidth = 1; c.font = '11px sans-serif';
        nv.forEach(function(p){
          c.strokeStyle = p.n.color; c.fillStyle = p.n.color;
          c.beginPath(); c.moveTo(xa, p.y); c.lineTo(xb, p.y); c.stroke();
          c.fillText(String(+p.n.val.toFixed(3)) + ' (' + p.precio.toFixed(DIGITS) + ')', xa + 5, p.y - 3);
        });
        c.strokeStyle = 'rgba(139,148,158,0.8)'; c.setLineDash([4, 4]);
        c.beginPath(); c.moveTo(g.x1, g.y1); c.lineTo(g.x2, g.y2); c.stroke();
        c.setLineDash([]);
        if (sel) { dibujarHandle(c, g.x1, g.y1, '#a78bfa'); dibujarHandle(c, g.x2, g.y2, '#a78bfa'); }

      } else if (el.tipo === 'text' && ok(g.x, g.y)) {
        c.font = '13px sans-serif';
        c.fillStyle = el.color || '#ffffff';
        c.fillText(el.texto || 'Texto', g.x, g.y);
        if (sel || hov) {
          var tw = c.measureText(el.texto || 'Texto').width;
          c.strokeStyle = 'rgba(88,166,255,0.8)'; c.lineWidth = 1; c.setLineDash([3, 3]);
          c.strokeRect(g.x - 4, g.y - 16, tw + 8, 22);
        }

      } else if (el.tipo === 'measure' && ok(g.x1, g.y1, g.x2, g.y2)) {
        var sube = el.price2 >= el.price1;
        var colM = sube ? '#2962ff' : '#f23645';
        var mw = g.x2 - g.x1, mh = g.y2 - g.y1;
        c.globalAlpha = 0.15; c.fillStyle = colM; c.fillRect(g.x1, g.y1, mw, mh);
        c.globalAlpha = 1; c.strokeStyle = colM; c.lineWidth = 1;
        c.strokeRect(g.x1, g.y1, mw, mh);

        var l1 = tiempoALogico(el.time1), l2 = tiempoALogico(el.time2);
        var barras = (l1 === null || l2 === null) ? 0 : Math.abs(Math.round(l2 - l1));
        var dif = el.price2 - el.price1;
        var pct = el.price1 ? (dif / el.price1) * 100 : 0;
        var textoDif = PIP > 0 ? (dif / PIP).toFixed(1) + ' pips' : dif.toFixed(DIGITS);
        var txt = (dif >= 0 ? '+' : '') + textoDif + ' (' + (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%)  ·  ' + barras + ' barras';
        c.font = '12px sans-serif';
        var pw = c.measureText(txt).width + 16;
        var px0 = (g.x1 + g.x2) / 2 - pw / 2;
        var py0 = sube ? Math.min(g.y1, g.y2) - 28 : Math.max(g.y1, g.y2) + 8;
        c.fillStyle = colM; c.fillRect(px0, py0, pw, 20);
        c.fillStyle = '#ffffff'; c.textBaseline = 'middle';
        c.fillText(txt, px0 + 8, py0 + 10);
        if (sel) { dibujarHandle(c, g.x1, g.y1, colM); dibujarHandle(c, g.x2, g.y2, colM); }
      }
      c.restore();
    }

    function fmtTiempo(t){
      var d = new Date(t * 1000);
      function p(n){ return (n < 10 ? '0' : '') + n; }
      return p(d.getUTCDate()) + '/' + p(d.getUTCMonth() + 1) + ' ' + p(d.getUTCHours()) + ':' + p(d.getUTCMinutes());
    }

    function badgePrecio(c, y, precio, fondo, texto, ap){
      if (!ok(y) || y < 0 || y > ap.h) return;
      var w = cssW - ap.w;
      c.save();
      c.fillStyle = fondo; c.fillRect(ap.w, y - 10, w, 20);
      c.fillStyle = texto; c.font = '11px sans-serif'; c.textBaseline = 'middle'; c.textAlign = 'left';
      c.fillText(precio.toFixed(DIGITS), ap.w + 6, y);
      c.restore();
    }

    function badgeTiempo(c, x, t, fondo, ap){
      var h = cssH - ap.h;
      if (!ok(x) || x < 0 || x > ap.w || h < 10) return;
      var w = 92;
      var bx = Math.max(0, Math.min(ap.w - w, x - w / 2));
      c.save();
      c.fillStyle = fondo; c.fillRect(bx, ap.h, w, h);
      c.fillStyle = '#ffffff'; c.font = '11px sans-serif'; c.textAlign = 'center'; c.textBaseline = 'middle';
      c.fillText(fmtTiempo(t), bx + w / 2, ap.h + h / 2);
      c.restore();
    }

    // Etiquetas sobre los ejes (se pintan fuera del recorte del área de trazado)
    function etiquetasEje(c, el, ap){
      if (el.tipo === 'hline'){
        badgePrecio(c, yDePrecio(el.price), el.price, el.color || '#f5c518', el.color ? '#ffffff' : '#0d1117', ap);
        return;
      }
      if (el.tipo === 'text') return;
      var col = el.tipo === 'fib' ? '#7c5cd6' : (el.tipo === 'measure' ? (el.price2 >= el.price1 ? '#2962ff' : '#f23645') : (el.color || '#2962ff'));
      badgePrecio(c, yDePrecio(el.price1), el.price1, col, '#ffffff', ap);
      badgePrecio(c, yDePrecio(el.price2), el.price2, col, '#ffffff', ap);
      badgeTiempo(c, xDeTiempo(el.time1), el.time1, col, ap);
      badgeTiempo(c, xDeTiempo(el.time2), el.time2, col, ap);
    }

    function pintar(){
      ctx.clearRect(0, 0, cssW, cssH);
      if (!serie || !datosActuales.length) return;
      var ap = areaTrazado();
      ctx.save();
      ctx.beginPath();
      ctx.rect(0, 0, ap.w, ap.h);
      ctx.clip();
      elementosDibujados.forEach(function(el, idx){
        dibujarElemento(ctx, el, idx === seleccionadoId, idx === hoverId);
      });
      if (dibujoEnCurso) dibujarElemento(ctx, dibujoEnCurso, true, false);
      ctx.restore();

      elementosDibujados.forEach(function(el, idx){
        if (idx === seleccionadoId || el.tipo === 'hline') etiquetasEje(ctx, el, ap);
      });
      if (dibujoEnCurso) etiquetasEje(ctx, dibujoEnCurso, ap);
    }

    var ultimaFirma = '';
    function firmaVista(){
      if (!datosActuales.length || !serie) return '';
      var ref = datosActuales[datosActuales.length - 1].close;
      var ts = chart.timeScale();
      return [
        serie.priceToCoordinate(ref),
        serie.priceToCoordinate(ref * 1.01),
        ts.logicalToCoordinate(0),
        ts.logicalToCoordinate(100)
      ].join('|');
    }

    function bucleRedibujo(){
      if (elementosDibujados.length > 0 || dibujoEnCurso) {
        var f = firmaVista();
        if (sucio || f !== ultimaFirma) { ultimaFirma = f; sucio = false; pintar(); }
      } else if (sucio) {
        sucio = false;
        pintar();
      }
      requestAnimationFrame(bucleRedibujo);
    }
    requestAnimationFrame(bucleRedibujo);

    // --- Herramientas ---
    // Bloquea el scroll/zoom del gráfico SOLO mientras se arrastra un dibujo
    function bloquearGrafico(b){
      try { chart.applyOptions({ handleScroll: !b, handleScale: !b }); } catch (e) {}
    }

    function cancelarDibujoEnCurso(){
      dibujoEnCurso = null; esperandoSegundoClick = false; inicioClick = null;
      redibujarTodo();
    }

    function activarHerramienta(toolName) {
      if (dibujoEnCurso && toolName !== activeTool) cancelarDibujoEnCurso();
      activeTool = toolName;
      document.querySelectorAll('.tvtool').forEach(function(b){
        var t = b.getAttribute('data-tool');
        if (t !== 'clear' && t !== 'lock') {
          if (t === toolName) { b.classList.add('active'); }
          else { b.classList.remove('active'); }
        }
      });
      setCursor(toolName === 'cross' ? '' : 'cur-dibujar');
    }

    document.querySelectorAll('.tvtool').forEach(function(btn){
      btn.addEventListener('click', function(){
        var tool = btn.getAttribute('data-tool');
        if (tool === 'clear') {
          if (elementosDibujados.length && confirm("¿Deseas limpiar todos los dibujos de este gráfico?")) {
            elementosDibujados = [];
            seleccionadoId = null; hoverId = null;
            confirmarCambio();
          }
          return;
        }
        if (tool === 'lock') {
          bloqueado = !bloqueado;
          btn.style.color = bloqueado ? '#3fb950' : '#8b949e';
          btn.title = bloqueado ? "Desbloquear dibujos" : "Bloquear dibujos";
          if (bloqueado) { seleccionadoId = null; hoverId = null; activarHerramienta('cross'); redibujarTodo(); }
          return;
        }
        activarHerramienta(tool);
      });
    });

    function posMouse(e){
      var r = wrapEl.getBoundingClientRect();
      return { x: e.clientX - r.left, y: e.clientY - r.top };
    }

    function actualizarDibujoEnCurso(pos, e){
      var pt = puntoDesdeMouse(pos.x, pos.y, magnetEfectivo(e));
      if (!pt || !dibujoEnCurso) return;
      dibujoEnCurso.time2 = pt.time;
      dibujoEnCurso.price2 = pt.price;
      redibujarTodo();
    }

    function finalizarDibujo(valido){
      if (!dibujoEnCurso) return;
      var d = dibujoEnCurso;
      dibujoEnCurso = null; esperandoSegundoClick = false; inicioClick = null;
      var g = geom(d);
      var largo = ok(g.x1, g.y1, g.x2, g.y2) ? Math.hypot(g.x2 - g.x1, g.y2 - g.y1) : 0;
      if (valido && largo > 3) {
        elementosDibujados.push(d);
        seleccionadoId = elementosDibujados.length - 1;
        confirmarCambio();
      } else {
        redibujarTodo();
      }
      activarHerramienta('cross');
    }

    function anclasOriginales(el){
      if (el.tipo === 'hline') return { price: el.price };
      if (el.tipo === 'text') return { l: tiempoALogico(el.time), price: el.price };
      return { l1: tiempoALogico(el.time1), price1: el.price1, l2: tiempoALogico(el.time2), price2: el.price2 };
    }

    function aplicarArrastre(pos, e){
      var el = elementosDibujados[arrastre.idx];
      if (!el) return;
      var o = arrastre.orig;
      if (arrastre.modo === 'move') {
        var l = chart.timeScale().coordinateToLogical(pos.x);
        var p = serie.coordinateToPrice(pos.y);
        if (l === null || p === null) return;
        var dl = l - arrastre.l0, dp = p - arrastre.p0;
        if (el.tipo === 'hline') {
          el.price = o.price + dp;
        } else if (el.tipo === 'text') {
          if (o.l === null) return;
          el.time = logicoATiempo(o.l + dl); el.price = o.price + dp;
        } else {
          if (o.l1 === null || o.l2 === null) return;
          el.time1 = logicoATiempo(o.l1 + dl); el.price1 = o.price1 + dp;
          el.time2 = logicoATiempo(o.l2 + dl); el.price2 = o.price2 + dp;
        }
      } else {
        var pt = puntoDesdeMouse(pos.x, pos.y, magnetEfectivo(e));
        if (!pt) return;
        if (arrastre.modo === 'p1') { el.time1 = pt.time; el.price1 = pt.price; }
        else { el.time2 = pt.time; el.price2 = pt.price; }
      }
      redibujarTodo();
    }

    // MOUSEDOWN (fase de captura: decide si el clic es del dibujo o del gráfico)
    wrapEl.addEventListener('mousedown', function(e){
      if (e.button !== 0 || bloqueado || !serie) return;
      var pos = posMouse(e);
      var ap = areaTrazado();
      if (pos.x > ap.w || pos.y > ap.h) return;   // ejes: los maneja el gráfico

      // 1) Segundo clic de un dibujo "clic-clic"
      if (dibujoEnCurso && esperandoSegundoClick) {
        e.preventDefault(); e.stopPropagation();
        bloquearGrafico(true);
        actualizarDibujoEnCurso(pos, e);
        finalizarDibujo(true);
        return;
      }

      // 2) Herramienta de dibujo activa: empezar un dibujo nuevo
      if (activeTool !== 'cross') {
        e.preventDefault(); e.stopPropagation();
        var pt = puntoDesdeMouse(pos.x, pos.y, magnetEfectivo(e));
        if (!pt) return;
        if (activeTool === 'hline') {
          elementosDibujados.push({ tipo: 'hline', price: pt.price });
          seleccionadoId = elementosDibujados.length - 1;
          confirmarCambio();
          activarHerramienta('cross');
        } else if (activeTool === 'text') {
          var textoPrompt = prompt("Introduce el texto analítico:", "Soporte Clave");
          if (textoPrompt) {
            elementosDibujados.push({ tipo: 'text', time: pt.time, price: pt.price, texto: textoPrompt });
            seleccionadoId = elementosDibujados.length - 1;
            confirmarCambio();
          }
          activarHerramienta('cross');
        } else {
          bloquearGrafico(true);
          dibujoEnCurso = { tipo: activeTool, time1: pt.time, price1: pt.price, time2: pt.time, price2: pt.price };
          inicioClick = { x: pos.x, y: pos.y };
          esperandoSegundoClick = false;
          seleccionadoId = null;
          redibujarTodo();
        }
        return;
      }

      // 3) Cursor normal: seleccionar / mover / editar un dibujo existente
      var hit = elementoBajo(pos.x, pos.y);
      if (hit) {
        e.preventDefault(); e.stopPropagation();
        bloquearGrafico(true);
        seleccionadoId = hit.idx;
        arrastre = {
          modo: hit.parte === 'body' ? 'move' : hit.parte,
          idx: hit.idx,
          l0: chart.timeScale().coordinateToLogical(pos.x),
          p0: serie.coordinateToPrice(pos.y),
          orig: anclasOriginales(elementosDibujados[hit.idx]),
          movido: false,
          x0: pos.x, y0: pos.y
        };
        redibujarTodo();
        return;
      }
      if (seleccionadoId !== null) { seleccionadoId = null; redibujarTodo(); }
      // Sin dibujo bajo el cursor: el gráfico procesa el clic con normalidad (scroll, zoom, crosshair)
    }, true);

    window.addEventListener('mousemove', function(e){
      var pos = posMouse(e);

      if (arrastre) {
        if (!arrastre.movido && Math.hypot(pos.x - arrastre.x0, pos.y - arrastre.y0) < 3) return;
        arrastre.movido = true;
        aplicarArrastre(pos, e);
        return;
      }
      if (dibujoEnCurso) { actualizarDibujoEnCurso(pos, e); return; }

      // Hover: resaltar y cambiar el cursor
      var nuevoHover = null, cls = '';
      var dentro = pos.x >= 0 && pos.y >= 0 && pos.x <= cssW && pos.y <= cssH;
      if (dentro && !bloqueado && activeTool === 'cross') {
        var ap = areaTrazado();
        if (pos.x <= ap.w && pos.y <= ap.h) {
          var h = elementoBajo(pos.x, pos.y);
          if (h) { nuevoHover = h.idx; cls = (h.parte === 'body') ? 'cur-mover' : 'cur-punto'; }
        }
      }
      if (nuevoHover !== hoverId) { hoverId = nuevoHover; redibujarTodo(); }
      setCursor(activeTool !== 'cross' ? 'cur-dibujar' : cls);
    });

    window.addEventListener('mouseup', function(e){
      if (arrastre) {
        var huboCambio = arrastre.movido;
        arrastre = null;
        if (huboCambio) confirmarCambio();
      } else if (dibujoEnCurso && !esperandoSegundoClick) {
        var pos = posMouse(e);
        var dist = inicioClick ? Math.hypot(pos.x - inicioClick.x, pos.y - inicioClick.y) : 0;
        if (dist > 6) { actualizarDibujoEnCurso(pos, e); finalizarDibujo(true); }
        else { esperandoSegundoClick = true; }   // clic simple: esperar el segundo clic
      }
      bloquearGrafico(false);
    });

    window.addEventListener('blur', function(){
      if (arrastre) {
        var huboCambio = arrastre.movido;
        arrastre = null;
        if (huboCambio) confirmarCambio();
      }
      bloquearGrafico(false);
    });

    // Atajos de teclado: Esc, Supr, Ctrl+Z, Ctrl+Y (hay que haber hecho clic antes dentro del gráfico)
    document.addEventListener('keydown', function(e){
      var tag = (e.target && e.target.tagName) || '';
      if (tag === 'INPUT' || tag === 'TEXTAREA') return;
      var k = e.key;
      if (k === 'Escape') {
        if (dibujoEnCurso) cancelarDibujoEnCurso();
        activarHerramienta('cross');
        if (seleccionadoId !== null) { seleccionadoId = null; redibujarTodo(); }
        return;
      }
      if ((k === 'Delete' || k === 'Backspace') && seleccionadoId !== null && !bloqueado) {
        e.preventDefault();
        elementosDibujados.splice(seleccionadoId, 1);
        seleccionadoId = null; hoverId = null;
        confirmarCambio();
        return;
      }
      if (e.ctrlKey || e.metaKey) {
        var kl = (k || '').toLowerCase();
        if (kl === 'z' && !e.shiftKey) { e.preventDefault(); deshacer(); }
        else if (kl === 'y' || (kl === 'z' && e.shiftKey)) { e.preventDefault(); rehacer(); }
      }
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

    function rsiDesde(ganancia, perdida){
      if (perdida === 0) return ganancia === 0 ? 50 : 100;
      return 100 - (100 / (1 + ganancia / perdida));
    }

    function calcularRSI(datos, periodo){
      var out = [];
      if (datos.length <= periodo) return out;

      for (var k = 0; k < periodo; k++){ out.push({ time: datos[k].time }); }

      var ganancias = 0, perdidas = 0;
      for (var i = 1; i <= periodo; i++){
        var cambio = datos[i].close - datos[i-1].close;
        if (cambio >= 0) ganancias += cambio;
        else perdidas -= cambio;
      }
      var mediaGanancia = ganancias / periodo;
      var mediaPerdida = perdidas / periodo;
      out.push({ time: datos[periodo].time, value: rsiDesde(mediaGanancia, mediaPerdida) });
      
      for (var n = periodo + 1; n < datos.length; n++){
        var cam = datos[n].close - datos[n-1].close;
        var g = cam >= 0 ? cam : 0;
        var p = cam < 0 ? -cam : 0;
        mediaGanancia = (mediaGanancia * (periodo - 1) + g) / periodo;
        mediaPerdida = (mediaPerdida * (periodo - 1) + p) / periodo;
        out.push({ time: datos[n].time, value: rsiDesde(mediaGanancia, mediaPerdida) });
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
        rightPriceScale: { borderColor: '#30363d', minimumWidth: 72, scaleMargins: { top: 0.1, bottom: 0.1 } },
        handleScroll: false,
        handleScale: false
      });
      serieRsi = chartRsi.addLineSeries({
        color: '#a78bfa', lineWidth: 2,
        priceFormat: { type: 'price', precision: 2, minMove: 0.01 }
      });
      serieRsi.createPriceLine({ price: 70, color: '#8b949e', lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: '' });
      serieRsi.createPriceLine({ price: 30, color: '#8b949e', lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: '' });
    }

    function actualizarIndicadoresActivos(){
      if (indicadores.sma20) {
        if (!seriesInd.sma20) seriesInd.sma20 = chart.addLineSeries({ color: '#f5c518', lineWidth: 2, priceLineVisible: false, priceFormat: PF });
        seriesInd.sma20.setData(calcularSMA(datosActuales, 20));
      } else if (seriesInd.sma20) {
        chart.removeSeries(seriesInd.sma20); seriesInd.sma20 = null;
      }

      if (indicadores.sma50) {
        if (!seriesInd.sma50) seriesInd.sma50 = chart.addLineSeries({ color: '#3399ff', lineWidth: 2, priceLineVisible: false, priceFormat: PF });
        seriesInd.sma50.setData(calcularSMA(datosActuales, 50));
      } else if (seriesInd.sma50) {
        chart.removeSeries(seriesInd.sma50); seriesInd.sma50 = null;
      }

      if (indicadores.ema20) {
        if (!seriesInd.ema20) seriesInd.ema20 = chart.addLineSeries({ color: '#ff6600', lineWidth: 2, priceLineVisible: false, priceFormat: PF });
        seriesInd.ema20.setData(calcularEMA(datosActuales, 20));
      } else if (seriesInd.ema20) {
        chart.removeSeries(seriesInd.ema20); seriesInd.ema20 = null;
      }

      if (indicadores.bollinger) {
        var bb = calcularBollinger(datosActuales, 20, 2);
        if (!seriesInd.bolsuper) {
          seriesInd.bolsuper = chart.addLineSeries({ color: 'rgba(41, 98, 255, 0.7)', lineWidth: 1, priceLineVisible: false, priceFormat: PF });
          seriesInd.bolmedia = chart.addLineSeries({ color: 'rgba(255, 152, 0, 0.7)', lineWidth: 1, priceLineVisible: false, priceFormat: PF });
          seriesInd.bolinf = chart.addLineSeries({ color: 'rgba(41, 98, 255, 0.7)', lineWidth: 1, priceLineVisible: false, priceFormat: PF });
        }
        seriesInd.bolsuper.setData(bb.superiores);
        seriesInd.bolmedia.setData(bb.medias);
        seriesInd.bolinf.setData(bb.inferiores);
      } else if (seriesInd.bolsuper) {
        chart.removeSeries(seriesInd.bolsuper); seriesInd.bolsuper = null;
        chart.removeSeries(seriesInd.bolmedia); seriesInd.bolmedia = null;
        chart.removeSeries(seriesInd.bolinf); seriesInd.bolinf = null;
      }

      if (indicadores.rsi) {
        inicializarRSIChart();
        if (serieRsi) {
          serieRsi.setData(calcularRSI(datosActuales, 14));
          var rango = chart.timeScale().getVisibleLogicalRange();
          if (rango && chartRsi) chartRsi.timeScale().setVisibleLogicalRange(rango);
        }
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
        'O<b style="color:' + color + '">' + v.open.toFixed(DIGITS) + '</b> ' +
        'H<b style="color:' + color + '">' + v.high.toFixed(DIGITS) + '</b> ' +
        'L<b style="color:' + color + '">' + v.low.toFixed(DIGITS) + '</b> ' +
        'C<b style="color:' + color + '">' + v.close.toFixed(DIGITS) + '</b> ' +
        '<b style="color:' + color + '">' + (variacion >= 0 ? '+' : '') + variacion.toFixed(2) + '%</b>';
      if (elVol) elVol.innerText = 'Vol. ' + fmtVol(v.volume);
    }

    function cargar(tf, n, ajustarFit){
      tfActual = tf;
      nBarrasActual = n;
      var miId = ++cargaId;
      cargando = true;
      fetch(API + "/velas/" + encodeURIComponent(SIMBOLO) + "?tf=" + tf + "&n=" + n)
        .then(function(r){
          if (!r.ok) throw new Error('HTTP ' + r.status);
          return r.json();
        })
        .then(function(velas){
          if (miId !== cargaId) return;
          cargando = false;
          if (velas && velas.length){
            datosActuales = velas;
            serie.setData(formatearDatos(velas, tipoActual));
            serieVolumen.setData(velas.map(aPuntoVolumen));
            if (ajustarFit === 'ultimas') {
              var nv = datosActuales.length;
              chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, nv - 150), to: nv + 8 });
            } else if (ajustarFit) {
              chart.timeScale().fitContent();
            }
            actualizarLeyenda(velas[velas.length - 1]);
            actualizarIndicadoresActivos();
            redibujarTodo();
          }
        })
        .catch(function(){
          if (miId !== cargaId) return;
          cargando = false;
          if (!datosActuales.length) {
            var elOhlc = document.getElementById('tv-ohlc-vals');
            if (elOhlc) elOhlc.innerText = 'Sin conexión con la API (' + API + ')';
          }
        });
    }

    cargar(tfActual, nBarrasActual, 'ultimas');

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
        redibujarTodo();
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
      if (cargando || pollEnCurso || !datosActuales.length) return;
      var tfLlamada = tfActual;
      var idLlamada = cargaId;
      pollEnCurso = true;
      fetch(API + "/ultima/" + encodeURIComponent(SIMBOLO) + "?tf=" + tfLlamada)
        .then(function(r){ return r.json(); })
        .then(function(v){
          if (tfLlamada !== tfActual || idLlamada !== cargaId) return;
          if (v && v.time){
            var ultima = datosActuales[datosActuales.length - 1];
            if (v.time < ultima.time) return;
            if (ultima.time === v.time){
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
        .catch(function(){})
        .then(function(){ pollEnCurso = false; });
    }, 1500);

    chart.subscribeCrosshairMove(function(param){
      if (!param || !param.time){
        if (datosActuales.length) actualizarLeyenda(datosActuales[datosActuales.length - 1]);
        return;
      }
      var idx = datosActuales.findIndex(function(d){ return d.time === param.time; });
      if (idx >= 0) actualizarLeyenda(datosActuales[idx]);
    });

        function marcarTF(tf){
      document.querySelectorAll('.tvtf').forEach(function(b){
        b.classList.toggle('active', b.getAttribute('data-tf') === tf);
      });
    }

    // Temporalidad (barra superior): carga el timeframe y muestra las últimas velas
    document.querySelectorAll('.tvtf').forEach(function(btn){
      btn.addEventListener('click', function(){
        var tf = btn.getAttribute('data-tf');
        marcarTF(tf);
        document.querySelectorAll('.tvrange').forEach(function(b){ b.classList.remove('active'); });
        cargar(tf, parseInt(btn.getAttribute('data-n'), 10), 'ultimas');
      });
    });

    // Rango (barra inferior): elige la temporalidad adecuada para ese periodo y lo ajusta completo
    document.querySelectorAll('.tvrange').forEach(function(btn){
      btn.addEventListener('click', function(){
        var tf = btn.getAttribute('data-tf');
        document.querySelectorAll('.tvrange').forEach(function(b){ b.classList.remove('active'); });
        btn.classList.add('active');
        marcarTF(tf);
        cargar(tf, parseInt(btn.getAttribute('data-n'), 10), true);
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


def _limpiar_simbolo(valor: str) -> str:
    """Quita los puntos suspensivos con que la lista de activos abrevia el símbolo."""
    return valor.replace("...", "").replace("…", "").strip()


def _info_simbolo(simbolo: str) -> Tuple[int, float]:
    """
    Devuelve (decimales, tamaño_del_pip) del símbolo según MT5.
    El pip es 0.0 si el activo no es forex.
    """
    digits = 5
    pip = 0.0
    try:
        mt5.symbol_select(simbolo, True)
        info = mt5.symbol_info(simbolo)
        if info is not None:
            digits = int(info.digits)
            es_forex = info.trade_calc_mode == getattr(mt5, "SYMBOL_CALC_MODE_FOREX", 0)
            if es_forex:
                pip = float(info.point) * (10 if digits in (3, 5) else 1)
    except Exception:
        pass
    return digits, pip


def renderizar_panel_central(main: Optional[ModuleType]):
    inicializar_mt5()

    activo_actual = st.session_state.get("activo_seleccionado", "EURUSD...")
    activo_visible = _limpiar_simbolo(activo_actual)
    digits, pip = _info_simbolo(activo_visible)

    @st.fragment(run_every="2s")
    def _cabecera_precio():
        info_tick = obtener_precio_actual(activo_visible)
        conectado = "error" not in info_tick
        if conectado:
            precio_actual = info_tick.get("last", 0) if info_tick.get("last", 0) > 0 else info_tick.get("bid", 0)
        else:
            precio_actual = 0.0
        bid = float(info_tick.get("bid", 0) or 0)
        ask = float(info_tick.get("ask", 0) or 0)
        conectado = conectado and precio_actual > 0

        clave = f"_prev_precio_{activo_visible}"
        clave_color = f"_color_precio_{activo_visible}"
        if conectado:
            anterior = st.session_state.get(clave, precio_actual)
            if precio_actual > anterior:
                color_var_activo = "#3fb950"
            elif precio_actual < anterior:
                color_var_activo = "#f85149"
            else:
                color_var_activo = st.session_state.get(clave_color, "#3fb950")
            st.session_state[clave] = precio_actual
            st.session_state[clave_color] = color_var_activo
        else:
            color_var_activo = "#8b949e"

        color_estado = "#3fb950" if conectado else "#f85149"
        texto_estado = "Conectado" if conectado else "Sin conexión"
        
        st.markdown(f"""
            <div style='background-color: #161b22; padding: 10px 16px; border-radius: 8px; border: 1px solid #30363d; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;'>
                <div style='display: flex; align-items: center; gap: 14px;'>
                    <span style='font-size: 20px; font-weight: bold; color: #ffffff;'>{escape(activo_visible)}</span>
                    <span style='background: #30363d; color: #8b949e; padding: 2px 8px; border-radius: 4px; font-size: 11px;'>XM / MT5</span>
                    <span style='font-size: 22px; font-weight: bold; font-family: monospace; color: {color_var_activo};'>{precio_actual:,.{digits}f}</span>
                    <span style='font-size: 14px; font-weight: 600; color: {color_var_activo};'>Bid: {bid:,.{digits}f} | Ask: {ask:,.{digits}f}</span>
                </div>
                <div style='font-size: 13px; color: #8b949e; font-weight: 600; display: flex; align-items: center; gap: 6px;'>
                    {texto_estado} <span style='color: {color_estado}; font-size: 16px;'>●</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    _cabecera_precio()

    html_chart = (
        _CHART_TEMPLATE
        .replace("__SIMBOLO_HTML__", escape(activo_visible))
        .replace("__SIMBOLO_JS__", json.dumps(activo_visible))
        .replace("__API_URL_JS__", json.dumps(API_URL))
        .replace("__DIGITS__", str(digits))
        .replace("__PIP__", json.dumps(pip))
    )
    components.html(html_chart, height=750)

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

                            fig = Figure(figsize=(8, 4), facecolor='#0d1117')
                            ax = fig.subplots()
                            ax.set_facecolor('#0d1117')
                            ax.tick_params(colors='#8b949e')
                            for borde in ax.spines.values():
                                borde.set_color('#30363d')
                            ax.plot(valores, color='#3fb950', linewidth=2, label=f'Tendencia {activo_encontrado}')
                            ax.fill_between(range(len(valores)), valores, float(np.min(valores) * 0.99), color='#238636', alpha=0.2)
                            ax.set_title(f"Análisis Técnico y Gráfico Renderizado (MT5) - {activo_encontrado}", color='white', fontsize=12, fontweight='bold')
                            ax.set_xlabel("Barras", color='#8b949e')
                            ax.set_ylabel("Precio", color='#8b949e')
                            ax.grid(True, color='#30363d', linestyle='--', alpha=0.5)
                            ax.legend(loc='upper left', facecolor='#161b22', edgecolor='#30363d', labelcolor='white')

                            os.makedirs("downloads", exist_ok=True)
                            imagen_filename = f"downloads/grafico_{activo_encontrado.lower()}_{int(time.time())}.png"
                            fig.savefig(imagen_filename, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())

                            imagen_resultado_path = imagen_filename
                            respuesta_final += f"\n\n*Gráfico interactivo e imagen renderizada con datos de MetaTrader 5 para **{activo_encontrado}**.*"

                    st.markdown(respuesta_final)
                    if chart_data_resultado is not None:
                        st.line_chart(chart_data_resultado)
                    if imagen_resultado_path is not None:
                        st.image(imagen_resultado_path, caption=f"Imagen renderizada del análisis", use_container_width=True)

                    st.session_state.mensajes_ui.append({
                        "role": "assistant",
                        "content": respuesta_final,
                        "chart_data": chart_data_resultado,
                        "imagen_path": imagen_resultado_path
                    })