// [grafico] Dibujo: Fibonacci (retroceso, extensión, canal, zonas, abanico, círculos, espiral, arcos, cuña, tridente abanico) y Gann
    // Los niveles de cada herramienta son editables: el.niveles = [{ v: valor, on: visible, c: color }, ...]
    function niv(lista){ return lista.map(function(x){ return { v: x[0], on: !!x[1], c: x[2] }; }); }
    var NIV_FIB = [[0, 1, '#787b86'], [0.236, 1, '#f23645'], [0.382, 1, '#ff9800'], [0.5, 1, '#4caf50'], [0.618, 1, '#089981'], [0.786, 1, '#00bcd4'],
      [1, 1, '#787b86'], [1.618, 1, '#2962ff'], [2.618, 1, '#f23645'], [3.618, 1, '#9c27b0'], [4.236, 1, '#e91e63'], [1.272, 0, '#9c6e1f'],
      [1.414, 0, '#b24d4d'], [2.272, 0, '#9c6e1f'], [2.414, 0, '#4c9a54'], [2, 0, '#1f7a6b'], [3, 0, '#6a5acd'], [3.272, 0, '#9c6e1f'],
      [3.414, 0, '#b24d4d'], [3.786, 0, '#4c9a54'], [4.272, 0, '#9c6e1f'], [4.414, 0, '#b24d4d'], [4.618, 0, '#4c9a54'], [4.764, 0, '#1f7a6b']];
    var NIV_EXT = [[0, 1, '#787b86'], [0.236, 1, '#f23645'], [0.382, 1, '#ff9800'], [0.5, 1, '#4caf50'], [0.618, 1, '#089981'], [0.786, 1, '#00bcd4'],
      [1, 1, '#787b86'], [1.272, 1, '#9c6e1f'], [1.618, 1, '#2962ff'], [2, 1, '#1f7a6b'], [2.618, 1, '#f23645'], [3.618, 0, '#9c27b0'], [4.236, 0, '#e91e63'],
      [1.414, 0, '#b24d4d'], [2.272, 0, '#9c6e1f'], [2.414, 0, '#4c9a54'], [3, 0, '#6a5acd']];
    var NIV_SIMPLE = [[0.236, 1, '#f23645'], [0.382, 1, '#ff9800'], [0.5, 1, '#4caf50'], [0.618, 1, '#089981'], [0.786, 1, '#00bcd4'], [1, 1, '#787b86'],
      [1.618, 0, '#2962ff'], [2.618, 0, '#f23645']];
    var NIV_ZONAS = [[0, 1, '#787b86'], [1, 1, '#787b86'], [2, 1, '#f23645'], [3, 1, '#ff9800'], [5, 1, '#4caf50'], [8, 1, '#089981'], [13, 1, '#00bcd4'],
      [21, 1, '#2962ff'], [34, 1, '#9c27b0'], [55, 1, '#e91e63'], [89, 1, '#9c6e1f'], [144, 0, '#787b86'], [233, 0, '#787b86']];
    var NIV_TIEMPO = [[0, 1, '#787b86'], [0.382, 1, '#ff9800'], [0.618, 1, '#089981'], [1, 1, '#787b86'], [1.382, 1, '#00bcd4'], [1.618, 1, '#2962ff'],
      [2, 1, '#1f7a6b'], [2.382, 1, '#9c27b0'], [2.618, 1, '#f23645'], [3, 1, '#6a5acd'], [3.382, 0, '#9c6e1f'], [3.618, 0, '#e91e63'], [4, 0, '#787b86'], [4.236, 0, '#e91e63']];
    var NIV_ABANICO = [[0, 0, '#787b86'], [0.25, 1, '#f23645'], [0.382, 1, '#ff9800'], [0.5, 1, '#4caf50'], [0.618, 1, '#089981'], [0.75, 1, '#00bcd4'], [0.786, 0, '#2962ff'], [1, 1, '#787b86']];
    var NIV_GANN_ABANICO = [[8, 1, '#f23645'], [5, 0, '#e91e63'], [4, 1, '#ff9800'], [3, 1, '#f5c518'], [2, 1, '#4caf50'], [1, 1, '#787b86'],
      [0.5, 1, '#089981'], [0.3333, 1, '#00bcd4'], [0.25, 1, '#2962ff'], [0.2, 0, '#9c27b0'], [0.125, 1, '#a78bfa']];
    var NIV_GANN_CAJA = [[0.25, 1, '#ff9800'], [0.382, 1, '#f5c518'], [0.5, 1, '#4caf50'], [0.618, 1, '#089981'], [0.75, 1, '#00bcd4']];
    var NIV_DEF = { fib: NIV_FIB, fib_extension: NIV_EXT, fib_channel: NIV_EXT, fib_timezone: NIV_ZONAS, fib_timetrend: NIV_TIEMPO, fib_circles: NIV_SIMPLE,
      fib_arcs: NIV_SIMPLE, fib_wedge: NIV_SIMPLE, fib_pitchfan: NIV_SIMPLE, fib_speedfan: NIV_ABANICO, gann_fan: NIV_GANN_ABANICO, gann_box: NIV_GANN_CAJA };
    function nivelesDe(el){ return (el.niveles && el.niveles.length) ? el.niveles : niv(NIV_DEF[el.tipo] || []); }
    function nivelesActivos(el){ return nivelesDe(el).filter(function(l){ return l.on && isFinite(Number(l.v)); }).map(function(l){ return { v: Number(l.v), c: l.c || '#787b86' }; }); }
    function fmtNivel(v){ return String(+Number(v).toFixed(3)); }
    function textoNivel(el, v, precio){
      var a = el.mostrarNivel === false ? '' : fmtNivel(v), b = (el.mostrarPrecio === false || precio === undefined) ? '' : '(' + precio.toFixed(DIGITS) + ')';
      return (a + ' ' + b).trim();
    }
    function etiquetaNivel(x, y, txt, col, al){ return { k: 't', x: x, y: y, txt: txt, fg: col, size: 11, al: al || 'l' }; }
    function lineaTend(el, pts){ return el.lineaTendencia === false ? [] : [{ k: 'l', pts: pts, d: 'dash', w: 1, col: el.colorTendencia || '#787b86' }]; }
    function rangoX(el, P, S){ var xa = Math.min.apply(null, P.map(function(q){ return q.x; })), xb = Math.max.apply(null, P.map(function(q){ return q.x; })); if (el.extIzq) xa = 0; if (el.extDer) xb = S.W; return [xa, xb]; }
    function rellenoFranjas(filas, xa, xb){   // franjas entre niveles consecutivos (ordenados por pantalla)
      var out = [];
      for (var i = 0; i < filas.length - 1; i++){
        var f = filas[i].l.v >= filas[i + 1].l.v ? filas[i] : filas[i + 1];
        out.push({ k: 'f', pts: rectPts(xa, filas[i].y, xb, filas[i + 1].y), a: 0.12, col: f.l.c, sinTocar: true });
      }
      return out;
    }
    function ordenarFilas(filas){ return filas.sort(function(a, b){ return a.y - b.y; }); }
    function regFib(id, o){
      if (o.niveles === undefined) o.niveles = true;
      if (o.etiquetas === undefined) o.etiquetas = true;
      if (o.sinColor === undefined) o.sinColor = true;
      o.col = o.col || '#787b86'; o.w = o.w || 1; o.fib = true;
      regHerramienta(id, o);
    }

    // ----- Retroceso de Fibonacci: el nivel 0 está en el SEGUNDO punto y el 1 en el primero (como en TradingView/XM) -----
    regFib('fib', { n: 2, ext: true, invertir: true, forma: function(el, P, S){
      if (P.length < 2) return [{ k: 'l', pts: P }];
      var p1 = el.price1, p2 = el.price2, inv = !!el.invertir, r = rangoX(el, P, S), xa = r[0], xb = r[1], filas = [];
      nivelesActivos(el).forEach(function(l){
        var pc = inv ? p1 + (p2 - p1) * l.v : p2 - (p2 - p1) * l.v, y = yDePrecio(pc);
        if (ok(y)) filas.push({ l: l, y: y, p: pc });
      });
      ordenarFilas(filas);
      var prims = rellenoFranjas(filas, xa, xb);
      filas.forEach(function(f){
        prims.push({ k: 'l', pts: [{ x: xa, y: f.y }, { x: xb, y: f.y }], col: f.l.c });
        prims.push(etiquetaNivel(el.extIzq ? xa + 4 : xa - 4, f.y - (el.extIzq ? 7 : 0), textoNivel(el, f.l.v, f.p), f.l.c, el.extIzq ? 'l' : 'r'));
      });
      return prims.concat(lineaTend(el, [P[0], P[1]]));
    } });

    // ----- Extensión de Fibonacci basada en tendencias (3 puntos) -----
    regFib('fib_extension', { n: 3, ext: true, invertir: true, forma: function(el, P, S){
      if (P.length < 3) return [{ k: 'l', pts: P }];
      var d = el.price2 - el.price1, base = el.price3, inv = !!el.invertir, r = rangoX(el, P, S), xa = r[0], xb = r[1], filas = [];
      nivelesActivos(el).forEach(function(l){
        var pc = inv ? base - d * l.v : base + d * l.v, y = yDePrecio(pc);
        if (ok(y)) filas.push({ l: l, y: y, p: pc });
      });
      ordenarFilas(filas);
      var prims = rellenoFranjas(filas, xa, xb);
      filas.forEach(function(f){
        prims.push({ k: 'l', pts: [{ x: xa, y: f.y }, { x: xb, y: f.y }], col: f.l.c });
        prims.push(etiquetaNivel(el.extIzq ? xa + 4 : xa - 4, f.y - (el.extIzq ? 7 : 0), textoNivel(el, f.l.v, f.p), f.l.c, el.extIzq ? 'l' : 'r'));
      });
      return prims.concat(lineaTend(el, [P[0], P[1], P[2]]));
    } });

    // ----- Canal de Fibonacci (3 puntos) -----
    regFib('fib_channel', { n: 3, ext: true, forma: function(el, P, S){
      if (P.length < 3) return [{ k: 'l', pts: P }];
      var v = pRes(P[1], P[0]), len = Math.hypot(v.x, v.y) || 1, nrm = { x: -v.y / len, y: v.x / len };
      var dist = (P[2].x - P[0].x) * nrm.x + (P[2].y - P[0].y) * nrm.y, filas = [], prims = [];
      nivelesActivos(el).forEach(function(l){
        var o = { x: nrm.x * dist * l.v, y: nrm.y * dist * l.v }, a = pMas(P[0], o), b = pMas(P[1], o);
        if (el.extDer) b = lejos(a, b);
        if (el.extIzq) a = lejos(b, a);
        filas.push({ l: l, a: a, b: b });
      });
      filas.sort(function(x, y){ return x.l.v - y.l.v; });
      for (var i = 0; i < filas.length - 1; i++) prims.push({ k: 'f', pts: [filas[i].a, filas[i].b, filas[i + 1].b, filas[i + 1].a], a: 0.1, col: filas[i + 1].l.c, sinTocar: true });
      filas.forEach(function(f){
        prims.push({ k: 'l', pts: [f.a, f.b], col: f.l.c });
        if (el.mostrarNivel !== false) prims.push(etiquetaNivel(f.b.x + 5, f.b.y, fmtNivel(f.l.v), f.l.c, 'l'));
      });
      return prims.concat(lineaTend(el, [P[0], P[1]]));
    } });

    // ----- Zona horaria de Fibonacci (2 puntos) y zona temporal basada en tendencias (3 puntos) -----
    function lineasVerticalesZona(el, S, base, unidad, tit){
      var ts = chart.timeScale(), prims = [];
      nivelesActivos(el).forEach(function(l){
        var x = ts.logicalToCoordinate(base + unidad * l.v);
        if (!ok(x) || x < -2 || x > S.W + 2) return;
        prims.push({ k: 'l', pts: [{ x: x, y: 0 }, { x: x, y: S.H }], col: l.c });
        if (el.mostrarNivel !== false) prims.push(etiquetaNivel(x + 3, 12, fmtNivel(l.v), l.c, 'l'));
      });
      return prims;
    }
    regFib('fib_timezone', { n: 2, forma: function(el, P, S){
      if (P.length < 2) return [{ k: 'l', pts: P }];
      var l1 = tiempoALogico(el.time1), l2 = tiempoALogico(el.time2); if (l1 === null || l2 === null || l1 === l2) return [{ k: 'l', pts: P }];
      return lineasVerticalesZona(el, S, l1, l2 - l1).concat(lineaTend(el, [P[0], P[1]]));
    } });
    regFib('fib_timetrend', { n: 3, forma: function(el, P, S){
      if (P.length < 3) return [{ k: 'l', pts: P }];
      var l1 = tiempoALogico(el.time1), l2 = tiempoALogico(el.time2), l3 = tiempoALogico(el.time3); if (l1 === null || l2 === null || l3 === null || l1 === l2) return [{ k: 'l', pts: P }];
      return lineasVerticalesZona(el, S, l3, l2 - l1).concat(lineaTend(el, [P[0], P[1], P[2]]));
    } });

    // ----- Círculos, espiral y arcos -----
    regFib('fib_circles', { n: 2, forma: function(el, P, S){
      if (P.length < 2) return [{ k: 'l', pts: P }];
      var c0 = pMed(P[0], P[1]), R = Math.hypot(P[1].x - P[0].x, P[1].y - P[0].y) / 2, prims = [];
      nivelesActivos(el).forEach(function(l){
        prims.push({ k: 'c', x: c0.x, y: c0.y, r: R * l.v, col: l.c, a: el.relleno ? 0.04 : 0 });
        if (el.mostrarNivel !== false) prims.push(etiquetaNivel(c0.x + R * l.v * 0.7071 + 3, c0.y - R * l.v * 0.7071, fmtNivel(l.v), l.c, 'l'));
      });
      return prims.concat(lineaTend(el, [P[0], P[1]]));
    } });
    regFib('fib_spiral', { n: 2, niveles: false, etiquetas: false, sinColor: false, invertir: true, col: '#a78bfa', w: 2, forma: function(el, P, S){
      if (P.length < 2) return [{ k: 'l', pts: P }];
      var c0 = P[0], vx = P[1].x - c0.x, vy = P[1].y - c0.y, R = Math.hypot(vx, vy) || 1, th0 = Math.atan2(vy, vx), dir = el.invertir ? -1 : 1;
      var b = Math.log(1.618034) / (Math.PI / 2), pts = [];
      for (var th = -7 * Math.PI; th <= 1.6 * Math.PI; th += Math.PI / 80){
        var r = R * Math.exp(b * th); if (r < 0.6) continue;
        pts.push({ x: c0.x + r * Math.cos(th0 + dir * th), y: c0.y + r * Math.sin(th0 + dir * th) });
      }
      return [{ k: 'l', pts: pts }, { k: 'l', pts: [P[0], P[1]], d: 'dot', w: 1 }];
    } });
    regFib('fib_arcs', { n: 2, forma: function(el, P, S){
      if (P.length < 2) return [{ k: 'l', pts: P }];
      var c0 = P[0], R = Math.hypot(P[1].x - c0.x, P[1].y - c0.y), th0 = Math.atan2(P[1].y - c0.y, P[1].x - c0.x), prims = [];
      nivelesActivos(el).forEach(function(l){
        var pts = muestrearArco(c0, R * l.v, th0 - Math.PI / 2, th0 + Math.PI / 2, 48);
        prims.push({ k: 'l', pts: pts, col: l.c });
        if (el.mostrarNivel !== false) prims.push(etiquetaNivel(c0.x + R * l.v * Math.cos(th0) + 4, c0.y + R * l.v * Math.sin(th0), fmtNivel(l.v), l.c, 'l'));
      });
      return prims.concat(lineaTend(el, [P[0], P[1]]));
    } });
    regFib('fib_wedge', { n: 3, forma: function(el, P, S){
      if (P.length < 3) return [{ k: 'l', pts: P }];
      var c0 = P[0], R = Math.hypot(P[1].x - c0.x, P[1].y - c0.y), a1 = Math.atan2(P[1].y - c0.y, P[1].x - c0.x), a2 = Math.atan2(P[2].y - c0.y, P[2].x - c0.x), prims = [];
      var d = ((a2 - a1) % (2 * Math.PI) + 3 * Math.PI) % (2 * Math.PI) - Math.PI;   // giro más corto de un brazo al otro
      var niveles = nivelesActivos(el), rMax = R * Math.max.apply(null, niveles.map(function(l){ return l.v; }).concat([1]));
      niveles.forEach(function(l){
        var pts = muestrearArco(c0, R * l.v, a1, a1 + d, 40);
        prims.push({ k: 'l', pts: pts, col: l.c });
        if (el.mostrarNivel !== false) prims.push(etiquetaNivel(pts[pts.length - 1].x + 4, pts[pts.length - 1].y, fmtNivel(l.v), l.c, 'l'));
      });
      return [{ k: 'f', pts: [c0].concat(muestrearArco(c0, rMax, a1, a1 + d, 40)), a: 0.05, sinTocar: true },
              { k: 'l', pts: [c0, { x: c0.x + rMax * Math.cos(a1), y: c0.y + rMax * Math.sin(a1) }], d: 'dash', w: 1, col: '#787b86' },
              { k: 'l', pts: [c0, { x: c0.x + rMax * Math.cos(a1 + d), y: c0.y + rMax * Math.sin(a1 + d) }], d: 'dash', w: 1, col: '#787b86' }].concat(prims);
    } });

    // ----- Tridente abanico y abanico de resistencia de velocidad -----
    regFib('fib_pitchfan', { n: 3, forma: function(el, P, S){
      if (P.length < 3) return [{ k: 'l', pts: P }];
      var prims = [], filas = [];
      nivelesActivos(el).forEach(function(l){
        var q = pMas(P[1], pRes(P[2], P[1]), l.v), f = ext(P[0], pRes(q, P[0]));
        filas.push({ l: l, f: f }); prims.push({ k: 'l', pts: [P[0], f], col: l.c });
        if (el.mostrarNivel !== false) prims.push(etiquetaNivel(q.x + 4, q.y, fmtNivel(l.v), l.c, 'l'));
      });
      var med = ext(P[0], pRes(pMed(P[1], P[2]), P[0]));
      prims.unshift({ k: 'l', pts: [P[0], med], col: '#787b86', w: 1.5 });
      filas.sort(function(a, b){ return a.l.v - b.l.v; });
      for (var i = 0; i < filas.length - 1; i++) prims.unshift({ k: 'f', pts: [P[0], filas[i].f, filas[i + 1].f], a: 0.07, col: filas[i + 1].l.c, sinTocar: true });
      return prims.concat([{ k: 'l', pts: [P[1], P[2]], d: 'dash', w: 1, col: '#787b86' }]);
    } });
    regFib('fib_speedfan', { n: 2, forma: function(el, P, S){
      if (P.length < 2) return [{ k: 'l', pts: P }];
      var o = P[0], dx = P[1].x - o.x, dy = P[1].y - o.y, prims = [];
      nivelesActivos(el).forEach(function(l){
        var hx = { x: P[1].x, y: o.y + dy * l.v }, vx = { x: o.x + dx * l.v, y: P[1].y };
        prims.push({ k: 'l', pts: [{ x: o.x, y: hx.y }, hx], col: l.c, w: 1, d: 'dot' }); prims.push({ k: 'l', pts: [{ x: vx.x, y: o.y }, vx], col: l.c, w: 1, d: 'dot' });
        prims.push({ k: 'l', pts: [o, lejos(o, hx)], col: l.c }); prims.push({ k: 'l', pts: [o, lejos(o, vx)], col: l.c });
        if (el.mostrarNivel !== false) { prims.push(etiquetaNivel(hx.x + 4, hx.y, fmtNivel(l.v), l.c, 'l')); prims.push(etiquetaNivel(vx.x, vx.y + 10, fmtNivel(l.v), l.c, 'c')); }
      });
      return prims.concat([{ k: 'l', pts: rectPts(o.x, o.y, P[1].x, P[1].y), cerrar: true, d: 'dash', w: 1, col: '#787b86' }]);
    } });

    // ================= GANN =================
    regFib('gann_fan', { n: 2, forma: function(el, P, S){
      if (P.length < 2) return [{ k: 'l', pts: P }];
      var o = P[0], vx = P[1].x - o.x, vy = P[1].y - o.y, prims = [];
      nivelesActivos(el).forEach(function(l){
        var f = ext(o, { x: vx, y: vy * l.v });
        prims.push({ k: 'l', pts: [o, f], col: l.c, w: l.v === 1 ? 2 : 1.3 });
        var rot = l.v >= 1 ? fmtNivel(l.v) + 'x1' : '1x' + fmtNivel(1 / l.v);
        if (el.mostrarNivel !== false) { var q = { x: o.x + vx, y: o.y + vy * l.v }; prims.push(etiquetaNivel(q.x + 4, q.y, rot, l.c, 'l')); }
      });
      return prims;
    } });
    function formaGrid(fijo){
      return function(el, P, S){
        if (P.length < 2) return [{ k: 'l', pts: P }];
        var x0 = P[0].x, y0 = P[0].y, dx = P[1].x - x0, dy = P[1].y - y0, prims = [];
        if (fijo) { var lado = Math.max(Math.abs(dx), Math.abs(dy)); dx = (dx >= 0 ? 1 : -1) * lado; dy = (dy >= 0 ? 1 : -1) * lado; }
        var n = Math.max(2, Math.min(24, Math.round(el.divisiones || 8))), x1 = x0 + dx, y1 = y0 + dy;
        prims.push({ k: 'f', pts: rectPts(x0, y0, x1, y1), a: 0.06, col: '#787b86', sinTocar: false });
        for (var i = 0; i <= n; i++){
          var f = i / n, major = (i % (n / 2) === 0);
          prims.push({ k: 'l', pts: [{ x: x0, y: y0 + dy * f }, { x: x1, y: y0 + dy * f }], w: major ? 1.4 : 0.8, col: '#787b86' });
          prims.push({ k: 'l', pts: [{ x: x0 + dx * f, y: y0 }, { x: x0 + dx * f, y: y1 }], w: major ? 1.4 : 0.8, col: '#787b86' });
        }
        prims.push({ k: 'l', pts: [{ x: x0, y: y0 }, { x: x1, y: y1 }], col: '#f23645' }); prims.push({ k: 'l', pts: [{ x: x0, y: y1 }, { x: x1, y: y0 }], col: '#2962ff' });
        prims.push({ k: 'l', pts: [{ x: x0, y: y0 + dy / 2 }, { x: x0 + dx / 2, y: y0 }, { x: x1, y: y0 + dy / 2 }, { x: x0 + dx / 2, y: y1 }], cerrar: true, w: 0.8, col: '#ff9800' });
        return prims;
      };
    }
    regFib('gann_square_fixed', { n: 2, niveles: false, etiquetas: false, sinColor: false, divisiones: true, w: 1, forma: formaGrid(true) });
    regFib('gann_square', { n: 2, niveles: false, etiquetas: false, sinColor: false, divisiones: true, w: 1, forma: formaGrid(false) });
    regFib('gann_box', { n: 2, forma: function(el, P, S){
      if (P.length < 2) return [{ k: 'l', pts: P }];
      var x0 = P[0].x, y0 = P[0].y, dx = P[1].x - x0, dy = P[1].y - y0, prims = [], niv_ = nivelesActivos(el);
      prims.push({ k: 'f', pts: rectPts(x0, y0, x0 + dx, y0 + dy), a: 0.06, col: '#787b86' });
      niv_.forEach(function(l){
        prims.push({ k: 'l', pts: [{ x: x0, y: y0 + dy * l.v }, { x: x0 + dx, y: y0 + dy * l.v }], col: l.c, w: 1 });
        prims.push({ k: 'l', pts: [{ x: x0 + dx * l.v, y: y0 }, { x: x0 + dx * l.v, y: y0 + dy }], col: l.c, w: 1 });
        if (el.mostrarNivel !== false) { prims.push(etiquetaNivel(x0 + dx + 4, y0 + dy * l.v, fmtNivel(l.v), l.c, 'l')); prims.push(etiquetaNivel(x0 + dx * l.v, y0 + dy + 10, fmtNivel(l.v), l.c, 'c')); }
      });
      prims.push({ k: 'l', pts: rectPts(x0, y0, x0 + dx, y0 + dy), cerrar: true, w: 1.5, col: '#787b86' });
      prims.push({ k: 'l', pts: [{ x: x0, y: y0 }, { x: x0 + dx, y: y0 + dy }], col: '#f23645', w: 1 }); prims.push({ k: 'l', pts: [{ x: x0, y: y0 + dy }, { x: x0 + dx, y: y0 }], col: '#2962ff', w: 1 });
      return prims;
    } });
