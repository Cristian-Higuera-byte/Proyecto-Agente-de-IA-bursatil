// [grafico] Creación del gráfico, volumen y tipos de serie
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
        // Línea del precio actual en BLANCO (neutra, como XM): así no se confunde ni se
        // monta con nuestras líneas de posición/orden (verde compra/TP, rojo venta/pérdida,
        // naranja SL). Dashed para leerse como "precio en vivo", no como un nivel propio.
        // lastValueVisible:false -> la ETIQUETA del eje la dibuja nuestro overlay
        // (componentes_plataforma/posiciones_grafico.py) para que quede del mismo tamaño que las
        // nuestras, pegada y llegando al borde; aquí solo queda la línea.
        serie.applyOptions({ priceLineVisible: true, priceLineColor: '#e6edf3',
                             priceLineWidth: 1, priceLineStyle: 2, lastValueVisible: false });
        if (typeof aplicarMarcasBT === 'function') aplicarMarcasBT();   // las operaciones del backtest se mantienen al cambiar de tipo de gráfico
      }
    }

    crearSerie(tipoActual);

