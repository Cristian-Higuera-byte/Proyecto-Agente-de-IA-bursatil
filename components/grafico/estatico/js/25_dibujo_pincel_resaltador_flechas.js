// [grafico] Dibujo: pincel, resaltador y flechas
    var estiloPincel = { color: COLOR_DEF.brush, ancho: ANCHO_DEF.brush };
    var trazoPincel = null;
    var cachePincel = new WeakMap();

    function firmaPincel(){
      var n = datosActuales.length;
      return n ? (n + ':' + datosActuales[0].time + ':' + datosActuales[n - 1].time + ':' + firmaVista()) : '';
    }

    function puntosPantalla(el){
      var firma = firmaPincel();
      var c = cachePincel.get(el);
      if (c && c.ref === el.puntos && c.firma === firma) return c.pts;
      var out = [];
      (el.puntos || []).forEach(function(q){
        var x = xDeTiempo(q[0]), y = yDePrecio(q[1]);
        if (ok(x, y)) out.push({ x: x, y: y });
      });
      cachePincel.set(el, { ref: el.puntos, firma: firma, pts: out });
      return out;
    }

    function trazarSuave(c, pts, col, ancho){
      var v = pts.filter(function(q){ return ok(q.x, q.y); });
      if (!v.length) return;
      c.save();
      c.strokeStyle = col; c.fillStyle = col; c.lineWidth = ancho;
      c.lineCap = 'round'; c.lineJoin = 'round';
      var punto = v.length === 1 || (v.length === 2 && v[0].x === v[1].x && v[0].y === v[1].y);
      if (punto) {
        c.beginPath(); c.arc(v[0].x, v[0].y, ancho / 2, 0, 2 * Math.PI); c.fill();
      } else {
        c.beginPath(); c.moveTo(v[0].x, v[0].y);
        for (var i = 1; i < v.length - 1; i++) {
          var mx = (v[i].x + v[i + 1].x) / 2, my = (v[i].y + v[i + 1].y) / 2;
          c.quadraticCurveTo(v[i].x, v[i].y, mx, my);
        }
        c.lineTo(v[v.length - 1].x, v[v.length - 1].y);
        c.stroke();
      }
      c.restore();
    }

    function dibujarPincel(c, el, sel, hov){
      var v = puntosPantalla(el);
      if (!v.length) return;
      var col = el.color || COLOR_DEF.brush, w = el.ancho || ANCHO_DEF.brush;
      if (sel) trazarSuave(c, v, 'rgba(88,166,255,0.35)', w + 6);
      trazarSuave(c, v, col, w + ((hov && !sel) ? 1 : 0));
    }

    function hitPincel(el, x, y){
      var v = puntosPantalla(el);
      if (!v.length) return false;
      var tol = Math.max(6, (el.ancho || ANCHO_DEF.brush) / 2 + 4);
      if (v.length === 1) return Math.hypot(x - v[0].x, y - v[0].y) <= tol;
      for (var i = 1; i < v.length; i++) {
        if (distSeg(x, y, v[i - 1].x, v[i - 1].y, v[i].x, v[i].y) <= tol) return true;
      }
      return false;
    }

    var dibujarElementoBase = dibujarElemento;
    dibujarElemento = function(c, el, sel, hov){
      if (el.tipo === 'brush') { dibujarPincel(c, el, sel, hov); return; }
      dibujarElementoBase(c, el, sel, hov);
    };

    var hitTestBase = hitTest;
    hitTest = function(el, x, y, sel){
      if (el.tipo === 'brush') return hitPincel(el, x, y) ? 'body' : null;
      return hitTestBase(el, x, y, sel);
    };

    var anclasOriginalesBase = anclasOriginales;
    anclasOriginales = function(el){
      if (el.tipo === 'brush') {
        return { pts: el.puntos.map(function(q){ return [tiempoALogico(q[0]), q[1]]; }) };
      }
      return anclasOriginalesBase(el);
    };

    var aplicarArrastreBase = aplicarArrastre;
    aplicarArrastre = function(pos, e){
      var el = arrastre ? elementosDibujados[arrastre.idx] : null;
      if (el && el.tipo === 'brush' && arrastre.modo === 'move') {
        var l = chart.timeScale().coordinateToLogical(pos.x), p = serie.coordinateToPrice(pos.y);
        if (l === null || p === null) return;
        var dl = l - arrastre.l0, dp = p - arrastre.p0;
        el.puntos = arrastre.orig.pts.map(function(q){
          return [Math.round(logicoATiempo(q[0] + dl)), q[1] + dp];
        });
        redibujarTodo();
        return;
      }
      aplicarArrastreBase(pos, e);
    };

    var pegarBase = pegar;
    pegar = function(){
      if (portapapeles && !bloqueado && serie) {
        var el0 = JSON.parse(portapapeles);
        if (el0.tipo === 'brush' && el0.puntos && el0.puntos.length) {
          var yRef = yDePrecio(el0.puntos[0][1]);
          var pDesp = ok(yRef) ? serie.coordinateToPrice(yRef + 24) : null;
          var dp0 = (pDesp !== null) ? (pDesp - el0.puntos[0][1]) : 0;
          el0.puntos = el0.puntos.map(function(q){
            var l = tiempoALogico(q[0]);
            return [l === null ? q[0] : Math.round(logicoATiempo(l + 4)), q[1] + dp0];
          });
          elementosDibujados.push(el0);
          seleccionadoId = elementosDibujados.length - 1;
          confirmarCambio();
          return;
        }
      }
      pegarBase();
    };

    var confirmarCambioBase = confirmarCambio;
    confirmarCambio = function(){
      var s = (seleccionadoId !== null) ? elementosDibujados[seleccionadoId] : null;
      if (s && s.tipo === 'brush') {
        if (s.color) estiloPincel.color = s.color;
        if (s.ancho) estiloPincel.ancho = s.ancho;
      }
      confirmarCambioBase();
    };

    var pintarPrevioPincel = pintar;
    pintar = function(){
      pintarPrevioPincel();
      if (!trazoPincel || !dibujosVisibles || !serie) return;
      var ap = areaTrazado(), ts = chart.timeScale();
      ctx.save();
      ctx.beginPath(); ctx.rect(0, 0, ap.w, ap.h); ctx.clip();
      trazarSuave(ctx, trazoPincel.pts.map(function(q){
        return { x: ts.logicalToCoordinate(q.l), y: yDePrecio(q.p) };
      }), trazoPincel.color, trazoPincel.ancho);
      ctx.restore();
    };

    function finalizarTrazo(){
      if (!trazoPincel) return;
      var t = trazoPincel;
      trazoPincel = null;
      bloquearGrafico(false);
      var puntos = [];
      t.pts.forEach(function(q){
        var tm = logicoATiempo(q.l);
        if (tm !== null) puntos.push([Math.round(tm), Math.round(q.p * 1e8) / 1e8]);
      });
      if (!puntos.length) { redibujarTodo(); return; }
      if (puntos.length === 1) puntos.push([puntos[0][0], puntos[0][1]]);
      elementosDibujados.push({ tipo: 'brush', puntos: puntos, color: t.color, ancho: t.ancho });
      seleccionadoId = elementosDibujados.length - 1;
      confirmarCambio();
      activarHerramienta(mantenerHerramienta ? 'brush' : 'cross');
    }

    function sumarPuntoTrazo(pos){
      var l = chart.timeScale().coordinateToLogical(pos.x), p = serie.coordinateToPrice(pos.y);
      if (l === null || p === null) return;
      var u = trazoPincel.ultimoPx;
      if (u && Math.hypot(pos.x - u.x, pos.y - u.y) < 2) return;
      trazoPincel.ultimoPx = { x: pos.x, y: pos.y };
      trazoPincel.pts.push({ l: l, p: p });
      redibujarTodo();
    }

    window.addEventListener('mousedown', function(e){
      if (activeTool !== 'brush' || e.button !== 0 || bloqueado || !serie || !datosActuales.length) return;
      if (!wrapEl.contains(e.target)) return;
      if (e.target.closest && e.target.closest('.tv-ui')) return;
      var pos = posMouse(e), ap = areaTrazado();
      if (pos.x < 0 || pos.y < 0 || pos.x > ap.w || pos.y > ap.h) return;
      e.preventDefault(); e.stopPropagation();
      bloquearGrafico(true);
      seleccionadoId = null; hoverId = null;
      trazoPincel = { pts: [], color: estiloPincel.color, ancho: estiloPincel.ancho, ultimoPx: null };
      sumarPuntoTrazo(pos);
    }, true);

    window.addEventListener('mousemove', function(e){
      if (!trazoPincel) return;
      if (activeTool !== 'brush') { trazoPincel = null; bloquearGrafico(false); redibujarTodo(); return; }
      if (!(e.buttons & 1)) { finalizarTrazo(); return; }
      var pos = posMouse(e), ap = areaTrazado();
      if (pos.x < 0 || pos.y < 0 || pos.x > ap.w || pos.y > ap.h) return;
      sumarPuntoTrazo(pos);
    });

    window.addEventListener('mouseup', function(){ finalizarTrazo(); });

    var estiloResaltador = { color: COLOR_DEF.highlighter, ancho: ANCHO_DEF.highlighter };
    var trazoResaltador = null;

    function dibujarResaltador(c, el, sel, hov){
      var v = puntosPantalla(el);
      if (!v.length) return;
      var w = el.ancho || ANCHO_DEF.highlighter;
      c.save();
      c.globalCompositeOperation = 'multiply';
      c.globalAlpha = sel ? 0.55 : 0.35;
      c.strokeStyle = el.color || COLOR_DEF.highlighter;
      c.lineWidth = w + ((hov && !sel) ? 2 : 0);
      c.lineCap = 'round'; c.lineJoin = 'round';
      c.beginPath();
      v.forEach(function(p, i){ i === 0 ? c.moveTo(p.x, p.y) : c.lineTo(p.x, p.y); });
      c.stroke();
      if (sel) {
        c.globalCompositeOperation = 'source-over';
        c.globalAlpha = 1;
        c.strokeStyle = 'rgba(88,166,255,0.5)';
        c.lineWidth = w + 8; c.setLineDash([6, 4]);
        c.beginPath();
        v.forEach(function(p, i){ i === 0 ? c.moveTo(p.x, p.y) : c.lineTo(p.x, p.y); });
        c.stroke();
      }
      c.restore();
    }

    var dibujarElementoBase2 = dibujarElemento;
    dibujarElemento = function(c, el, sel, hov){
      if (el.tipo === 'highlighter') { dibujarResaltador(c, el, sel, hov); return; }
      dibujarElementoBase2(c, el, sel, hov);
    };

    var hitTestBase2 = hitTest;
    hitTest = function(el, x, y, sel){
      if (el.tipo === 'highlighter') return hitPincel(el, x, y) ? 'body' : null;
      return hitTestBase2(el, x, y, sel);
    };

    var anclasOriginalesBase2 = anclasOriginales;
    anclasOriginales = function(el){
      if (el.tipo === 'highlighter') return { pts: el.puntos.map(function(q){ return [tiempoALogico(q[0]), q[1]]; }) };
      return anclasOriginalesBase2(el);
    };

    var aplicarArrastreBase2 = aplicarArrastre;
    aplicarArrastre = function(pos, e){
      var el = arrastre ? elementosDibujados[arrastre.idx] : null;
      if (el && el.tipo === 'highlighter' && arrastre.modo === 'move') {
        var l = chart.timeScale().coordinateToLogical(pos.x), p = serie.coordinateToPrice(pos.y);
        if (l === null || p === null) return;
        var dl = l - arrastre.l0, dp = p - arrastre.p0;
        el.puntos = arrastre.orig.pts.map(function(q){ return [Math.round(logicoATiempo(q[0] + dl)), q[1] + dp]; });
        redibujarTodo(); return;
      }
      aplicarArrastreBase2(pos, e);
    };

    window.addEventListener('mousedown', function(e){
      if (activeTool !== 'highlighter' || e.button !== 0 || bloqueado || !serie || !datosActuales.length) return;
      if (!wrapEl.contains(e.target)) return;
      if (e.target.closest && e.target.closest('.tv-ui')) return;
      var pos = posMouse(e), ap = areaTrazado();
      if (pos.x < 0 || pos.y < 0 || pos.x > ap.w || pos.y > ap.h) return;
      e.preventDefault(); e.stopPropagation();
      bloquearGrafico(true);
      seleccionadoId = null; hoverId = null;
      trazoResaltador = { pts: [], color: estiloResaltador.color, ancho: estiloResaltador.ancho, ultimoPx: null };
      var l = chart.timeScale().coordinateToLogical(pos.x), p = serie.coordinateToPrice(pos.y);
      if (l !== null && p !== null) trazoResaltador.pts.push({ l: l, p: p });
    }, true);

    window.addEventListener('mousemove', function(e){
      if (!trazoResaltador) return;
      if (activeTool !== 'highlighter') { trazoResaltador = null; bloquearGrafico(false); redibujarTodo(); return; }
      if (!(e.buttons & 1)) { finalizarResaltador(); return; }
      var pos = posMouse(e), ap = areaTrazado();
      if (pos.x < 0 || pos.y < 0 || pos.x > ap.w || pos.y > ap.h) return;
      var u = trazoResaltador.ultimoPx;
      if (u && Math.hypot(pos.x - u.x, pos.y - u.y) < 3) return;
      trazoResaltador.ultimoPx = { x: pos.x, y: pos.y };
      var l = chart.timeScale().coordinateToLogical(pos.x), p = serie.coordinateToPrice(pos.y);
      if (l !== null && p !== null) { trazoResaltador.pts.push({ l: l, p: p }); redibujarTodo(); }
    });

    function finalizarResaltador(){
      if (!trazoResaltador) return;
      var t = trazoResaltador; trazoResaltador = null;
      bloquearGrafico(false);
      var puntos = t.pts.map(function(q){ return [Math.round(logicoATiempo(q.l)), Math.round(q.p * 1e8) / 1e8]; });
      if (!puntos.length) { redibujarTodo(); return; }
      if (puntos.length === 1) puntos.push([puntos[0][0], puntos[0][1]]);
      elementosDibujados.push({ tipo: 'highlighter', puntos: puntos, color: t.color, ancho: t.ancho });
      seleccionadoId = elementosDibujados.length - 1;
      confirmarCambio();
      activarHerramienta(mantenerHerramienta ? 'highlighter' : 'cross');
    }

    window.addEventListener('mouseup', function(){ finalizarResaltador(); });

    var ARROW_CFG = {
      arrow_up:    { color: '#3fb950', label: '▲' },
      arrow_down:  { color: '#f85149', label: '▼' },
      arrow_left:  { color: '#58a6ff', label: '◄' },
      arrow_right: { color: '#ff9800', label: '►' }
    };
    Object.keys(ARROW_CFG).forEach(function(t){
      COLOR_DEF[t] = ARROW_CFG[t].color;
      ANCHO_DEF[t] = 14;
      TIPOS_COLOR[t] = 1;
    });

    var ARROW_DIRS = {
      arrow_up:    function(c, x, y, r){ c.moveTo(x, y - r); c.lineTo(x + r * 0.75, y + r * 0.6); c.lineTo(x - r * 0.75, y + r * 0.6); c.closePath(); },
      arrow_down:  function(c, x, y, r){ c.moveTo(x, y + r); c.lineTo(x + r * 0.75, y - r * 0.6); c.lineTo(x - r * 0.75, y - r * 0.6); c.closePath(); },
      arrow_left:  function(c, x, y, r){ c.moveTo(x - r, y); c.lineTo(x + r * 0.6, y - r * 0.75); c.lineTo(x + r * 0.6, y + r * 0.75); c.closePath(); },
      arrow_right: function(c, x, y, r){ c.moveTo(x + r, y); c.lineTo(x - r * 0.6, y - r * 0.75); c.lineTo(x - r * 0.6, y + r * 0.75); c.closePath(); }
    };

    function coordFlecha(el){
      var x = xDeTiempo(el.time1), y = yDePrecio(el.price1);
      return ok(x, y) ? { x: x, y: y } : null;
    }

    function dibujarFlecha(c, el, sel, hov){
      var g = coordFlecha(el); if (!g) return;
      var cfg = ARROW_CFG[el.tipo], col = el.color || cfg.color;
      var r = (el.ancho || 14) + (hov && !sel ? 2 : 0);
      c.save();
      c.beginPath();
      ARROW_DIRS[el.tipo](c, g.x, g.y, r);
      c.fillStyle = col;
      c.globalAlpha = sel ? 1 : 0.85;
      c.fill();
      if (sel) {
        c.strokeStyle = '#ffffff'; c.lineWidth = 1.5; c.globalAlpha = 0.9; c.stroke();
        dibujarHandle(c, g.x, g.y, col);
      }
      c.restore();
      badgePrecio(c, g.y, el.price1, col, '#fff', areaTrazado());
    }

    function hitFlecha(el, x, y){
      var g = coordFlecha(el); if (!g) return false;
      var r = (el.ancho || 14) + 6;
      return Math.hypot(x - g.x, y - g.y) <= r;
    }

    var dibujarElementoBase3 = dibujarElemento;
    dibujarElemento = function(c, el, sel, hov){
      if (ARROW_CFG[el.tipo]) { dibujarFlecha(c, el, sel, hov); return; }
      dibujarElementoBase3(c, el, sel, hov);
    };

    var hitTestBase3 = hitTest;
    hitTest = function(el, x, y, sel){
      if (ARROW_CFG[el.tipo]) return hitFlecha(el, x, y) ? 'body' : null;
      return hitTestBase3(el, x, y, sel);
    };

