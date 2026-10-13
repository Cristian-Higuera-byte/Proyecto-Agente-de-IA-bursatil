// [grafico] Indicadores: paneles de osciladores y actualización
    var DEF_PANES = {
      rsi:        'RSI (14)',
      macd:       'MACD (12, 26, 9)',
      stochastic: 'Estocástico (14, 3, 3)',
      atr:        'ATR (14)'
    };
    var PF_OSC = { type: 'price', precision: DIGITS + 1, minMove: Math.pow(10, -(DIGITS + 1)) };
    var PF_PCT = { type: 'price', precision: 2, minMove: 0.01 };
    function rango0a100(){ return { priceRange: { minValue: 0, maxValue: 100 } }; }

    function crearPane(id){
      if (PANES[id]) return PANES[id];
      var cont = document.getElementById('osc-panes');
      var tb = document.getElementById('tv-toolbar-left');
      cont.style.marginLeft = (tb ? tb.offsetWidth : 0) + 'px';   // alinea las barras con las del gráfico principal
      cont.style.display = 'flex';
      var el = document.createElement('div'); el.className = 'osc-pane';
      var cuerpo = document.createElement('div'); cuerpo.className = 'osc-cuerpo';
      var tit = document.createElement('div'); tit.className = 'osc-titulo';
      tit.appendChild(document.createTextNode(DEF_PANES[id]));
      var x = document.createElement('button'); x.className = 'osc-x'; x.title = 'Quitar indicador'; x.textContent = String.fromCharCode(215);
      x.addEventListener('click', function(){ indicadores[id] = false; actualizarIndicadoresActivos(); guardarConfig(); });
      tit.appendChild(x);
      el.appendChild(cuerpo); el.appendChild(tit); cont.appendChild(el);
      var ch = LightweightCharts.createChart(cuerpo, {
        autoSize: true,
        layout: { background: { color: '#0d1117' }, textColor: '#d1d4dc', fontSize: 11 },
        grid: { vertLines: { color: '#161b22' }, horzLines: { color: '#161b22' } },
        timeScale: { visible: false },
        rightPriceScale: { borderColor: '#30363d', minimumWidth: 72, scaleMargins: { top: 0.15, bottom: 0.1 } },
        handleScroll: false,
        handleScale: false
      });
      PANES[id] = { el: el, chart: ch, s: {} };
      reajustarPanes();
      var r = chart.timeScale().getVisibleLogicalRange();
      if (r) ch.timeScale().setVisibleLogicalRange(r);
      return PANES[id];
    }

    function quitarPane(id){
      var p = PANES[id];
      if (!p) return;
      p.chart.remove(); p.el.parentNode.removeChild(p.el);
      delete PANES[id];
      reajustarPanes();
      if (!Object.keys(PANES).length) document.getElementById('osc-panes').style.display = 'none';
    }

    // Altura de cada panel: 110 px si hay uno; con varios se reparten ~200 px para no aplastar el gráfico principal
    function reajustarPanes(){
      var ids = Object.keys(PANES), h = ids.length ? Math.floor(Math.min(110, 200 / ids.length)) : 0;
      ids.forEach(function(id){ PANES[id].el.style.height = h + 'px'; });
    }

    function sincronizarPanes(range){
      if (!range) return;
      Object.keys(PANES).forEach(function(id){ PANES[id].chart.timeScale().setVisibleLogicalRange(range); });
    }

    function actualizarIndicadoresActivos(){
      if (indicadores.sma20 && !modoComparar) {
        if (!seriesInd.sma20) seriesInd.sma20 = chart.addLineSeries({ color: '#f5c518', lineWidth: 2, priceLineVisible: false, priceFormat: PF });
        seriesInd.sma20.setData(calcularSMA(datosActuales, 20));
      } else if (seriesInd.sma20) {
        chart.removeSeries(seriesInd.sma20); seriesInd.sma20 = null;
      }

      if (indicadores.sma50 && !modoComparar) {
        if (!seriesInd.sma50) seriesInd.sma50 = chart.addLineSeries({ color: '#3399ff', lineWidth: 2, priceLineVisible: false, priceFormat: PF });
        seriesInd.sma50.setData(calcularSMA(datosActuales, 50));
      } else if (seriesInd.sma50) {
        chart.removeSeries(seriesInd.sma50); seriesInd.sma50 = null;
      }

      if (indicadores.sma200 && !modoComparar) {
        if (!seriesInd.sma200) seriesInd.sma200 = chart.addLineSeries({ color: '#a78bfa', lineWidth: 2, priceLineVisible: false, priceFormat: PF });
        seriesInd.sma200.setData(calcularSMA(datosActuales, 200));
      } else if (seriesInd.sma200) {
        chart.removeSeries(seriesInd.sma200); seriesInd.sma200 = null;
      }

      if (indicadores.ema20 && !modoComparar) {
        if (!seriesInd.ema20) seriesInd.ema20 = chart.addLineSeries({ color: '#ff6600', lineWidth: 2, priceLineVisible: false, priceFormat: PF });
        seriesInd.ema20.setData(calcularEMA(datosActuales, 20));
      } else if (seriesInd.ema20) {
        chart.removeSeries(seriesInd.ema20); seriesInd.ema20 = null;
      }

      if (indicadores.ema50 && !modoComparar) {
        if (!seriesInd.ema50) seriesInd.ema50 = chart.addLineSeries({ color: '#e056fd', lineWidth: 2, priceLineVisible: false, priceFormat: PF });
        seriesInd.ema50.setData(calcularEMA(datosActuales, 50));
      } else if (seriesInd.ema50) {
        chart.removeSeries(seriesInd.ema50); seriesInd.ema50 = null;
      }

      if (indicadores.bollinger && !modoComparar) {
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

      // --- Osciladores: cada uno en su propio panel, con su escala ---
      if (indicadores.rsi) {
        var pr = crearPane('rsi');
        if (!pr.s.rsi) {
          pr.s.rsi = pr.chart.addLineSeries({ color: '#a78bfa', lineWidth: 2, priceLineVisible: false, priceFormat: PF_PCT, autoscaleInfoProvider: rango0a100 });
          [70, 30].forEach(function(n){ pr.s.rsi.createPriceLine({ price: n, color: '#8b949e', lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: '' }); });
        }
        pr.s.rsi.setData(calcularRSI(datosActuales, 14));
      } else { quitarPane('rsi'); }

      if (indicadores.macd) {
        var pm = crearPane('macd');
        var mc = calcularMACD(datosActuales, 12, 26, 9);
        if (!pm.s.hist) {
          pm.s.hist = pm.chart.addHistogramSeries({ priceLineVisible: false, lastValueVisible: false, priceFormat: PF_OSC });
          pm.s.macd = pm.chart.addLineSeries({ color: '#2962ff', lineWidth: 2, priceLineVisible: false, lastValueVisible: false, priceFormat: PF_OSC });
          pm.s.sig = pm.chart.addLineSeries({ color: '#ff9800', lineWidth: 2, priceLineVisible: false, lastValueVisible: false, priceFormat: PF_OSC });
          pm.s.macd.createPriceLine({ price: 0, color: '#8b949e', lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: '' });
        }
        pm.s.hist.setData(mc.hist);
        pm.s.macd.setData(mc.macd);
        pm.s.sig.setData(mc.signal);
      } else { quitarPane('macd'); }

      if (indicadores.stochastic) {
        var ps = crearPane('stochastic');
        var es = calcularEstocastico(datosActuales, 14, 3, 3);
        if (!ps.s.k) {
          ps.s.k = ps.chart.addLineSeries({ color: '#2962ff', lineWidth: 2, priceLineVisible: false, priceFormat: PF_PCT, autoscaleInfoProvider: rango0a100 });
          ps.s.d = ps.chart.addLineSeries({ color: '#ff9800', lineWidth: 2, priceLineVisible: false, priceFormat: PF_PCT, autoscaleInfoProvider: rango0a100 });
          [80, 20].forEach(function(n){ ps.s.k.createPriceLine({ price: n, color: '#8b949e', lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: '' }); });
        }
        ps.s.k.setData(es.k);
        ps.s.d.setData(es.d);
      } else { quitarPane('stochastic'); }

      if (indicadores.atr) {
        var pa = crearPane('atr');
        if (!pa.s.atr) pa.s.atr = pa.chart.addLineSeries({ color: '#ff9800', lineWidth: 2, priceLineVisible: false, priceFormat: PF_OSC });
        pa.s.atr.setData(calcularATR(datosActuales, 14));
      } else { quitarPane('atr'); }

      if (indicadores.parabolic && !modoComparar) {
        if (!seriesInd.sar) seriesInd.sar = chart.addLineSeries({ color: '#f85149', lineWidth: 1, lineVisible: false, pointMarkersVisible: true, pointMarkersRadius: 2, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, priceFormat: PF });
        seriesInd.sar.setData(calcularParabolicSAR(datosActuales));
      } else if (seriesInd.sar) {
        chart.removeSeries(seriesInd.sar); seriesInd.sar = null;
      }
    }

    // En tiempo real (cada tick) no se recalcula todo cada vez: como mucho una vez cada 0,6 s
    var ultCalcInd = 0, timerInd = null;
    function actualizarIndicadoresTick(){
      if (!Object.keys(indicadores).some(function(k){ return indicadores[k]; })) return;
      var ahora = Date.now();
      if (ahora - ultCalcInd >= 600) { ultCalcInd = ahora; actualizarIndicadoresActivos(); return; }
      if (!timerInd) timerInd = setTimeout(function(){ timerInd = null; ultCalcInd = Date.now(); actualizarIndicadoresActivos(); }, 600);
    }

