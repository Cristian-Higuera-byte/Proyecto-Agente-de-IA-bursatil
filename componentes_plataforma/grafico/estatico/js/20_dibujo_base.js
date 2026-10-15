// [grafico] Dibujo: estado, historial, lienzo y conversión de coordenadas
    // ==========================================================================
    // SISTEMA DE DIBUJO PROFESIONAL CON MENÚ FLOTANTE DE LÍNEAS
    // ==========================================================================
    var canvas = document.getElementById('drawing-canvas');
    var ctx = canvas.getContext('2d');
    var wrapEl = document.getElementById('chart-wrapper');
    var activeTool = 'cross';
    var bloqueado = false;
    var imanActivo = true;

    var seleccionadoId = null;
    var hoverId = null;
    var dibujoEnCurso = null;
    var esperandoSegundoClick = false;
    var inicioClick = null;
    var arrastre = null;

    var NIVELES_FIB = [
      { val: 0.0,   color: '#f85149' }, { val: 0.236, color: '#ff9800' },
      { val: 0.382, color: '#f5c518' }, { val: 0.5,   color: '#3fb950' },
      { val: 0.618, color: '#58a6ff' }, { val: 0.786, color: '#a78bfa' },
      { val: 1.0,   color: '#f85149' }
    ];
    // Extensión de Fibonacci (basada en tendencia): se proyecta desde el punto C
    var NIVELES_FIB_EXT = [
      { val: 0.0,   color: '#f85149' }, { val: 0.236, color: '#ff9800' },
      { val: 0.382, color: '#f5c518' }, { val: 0.5,   color: '#3fb950' },
      { val: 0.618, color: '#58a6ff' }, { val: 0.786, color: '#a78bfa' },
      { val: 1.0,   color: '#f85149' }, { val: 1.272, color: '#26c6da' },
      { val: 1.618, color: '#e056fd' }, { val: 2.0,   color: '#ff9800' },
      { val: 2.618, color: '#58a6ff' }
    ];
    // Canal de Fibonacci: rectas paralelas a la base A-B, separadas en proporción a la distancia hasta C
    var NIVELES_FIB_CANAL = [
      { val: 0.0,   color: '#8b949e' }, { val: 0.236, color: '#ff9800' },
      { val: 0.382, color: '#f5c518' }, { val: 0.5,   color: '#3fb950' },
      { val: 0.618, color: '#58a6ff' }, { val: 0.786, color: '#a78bfa' },
      { val: 1.0,   color: '#f85149' }, { val: 1.618, color: '#e056fd' },
      { val: 2.618, color: '#26c6da' }
    ];

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
      sincronizarPanes(range);
    });

    function ok(){
      for (var i = 0; i < arguments.length; i++){
        var v = arguments[i];
        if (v === null || v === undefined || typeof v !== 'number' || !isFinite(v)) return false;
      }
      return true;
    }

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

    function puntoVisual(el, n){
      var t = el['time' + n], p = el['price' + n];
      return { x: xDeTiempo(t), y: yDePrecio(p) };
    }

    function geom(el){
      if (el.tipo === 'hline') return { y: yDePrecio(el.price) };
      if (el.tipo === 'vline') return { x: xDeTiempo(el.time) };
      if (el.tipo === 'text') return { x: xDeTiempo(el.time), y: yDePrecio(el.price) };
      if (el.tipo === 'crossline') return { x: xDeTiempo(el.time), y: yDePrecio(el.price) };
      var g = {};
      for (var n = 1; n <= 3; n++) {
        if (el['time' + n] === undefined) break;
        var q = puntoVisual(el, n);
        g['x' + n] = q.x; g['y' + n] = q.y;
      }
      if (!ok(g.x1, g.y1, g.x2, g.y2)) return null;
      return g;
    }

