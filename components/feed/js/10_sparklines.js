  // --- Mini-gráficos (sparklines) -----------------------------------------
  function sembrarSparks(){
    D.querySelectorAll('[data-pj-spark]').forEach(function(el){
      var s = el.getAttribute('data-pj-spark');
      var v = (el.getAttribute('data-pj-vals') || '').split(',').map(parseFloat)
                .filter(function(x){ return isFinite(x); });
      // La semilla del servidor (histórico M1) se usa UNA vez por símbolo: los
      // ticks ya recibidos se agregan detrás. Si aún no trae histórico real
      // (< 5 puntos, símbolo recién agregado) se reintenta en el próximo refresco.
      if (sembrado[s] || !v.length) return;
      if (v.length >= 5){
        spark[s] = v.concat(spark[s] || []).slice(-SPARK_MAX);
        sembrado[s] = true;
      } else if (!spark[s]) {
        spark[s] = v.slice();
      }
      sparkT[s] = Date.now();
    });
  }
  function empujarSpark(s, precio){
    if (!precio) return;
    var buf = spark[s] || (spark[s] = []);
    var ahora = Date.now();
    if (!buf.length || ahora - (sparkT[s] || 0) >= SPARK_PASO){
      buf.push(precio); sparkT[s] = ahora;
      if (buf.length > SPARK_MAX) buf.splice(0, buf.length - SPARK_MAX);
    } else {
      buf[buf.length - 1] = precio;          // dentro del paso: mueve el último punto
    }
  }
  function svgSpark(s, vals, col){
    var w = 92, h = 40, pad = 3;
    if (vals.length < 2) vals = [vals[0], vals[0]];
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals), rng = (hi - lo) || 1;
    var n = vals.length, pts = [];
    for (var i = 0; i < n; i++){
      var x = i * (w / (n - 1)), y = h - pad - ((vals[i] - lo) / rng) * (h - 2 * pad);
      pts.push(x.toFixed(1) + ',' + y.toFixed(1));
    }
    var linea = pts.join(' '), gid = 'pjs' + s.replace(/\W/g, '');
    return "<svg xmlns='http://www.w3.org/2000/svg' width='" + w + "' height='" + h +
      "' viewBox='0 0 " + w + " " + h + "' preserveAspectRatio='none'>" +
      "<defs><linearGradient id='" + gid + "' x1='0' y1='0' x2='0' y2='1'>" +
      "<stop offset='0' stop-color='" + col + "' stop-opacity='0.30'/>" +
      "<stop offset='1' stop-color='" + col + "' stop-opacity='0'/></linearGradient></defs>" +
      "<polygon points='0," + h + " " + linea + " " + w + "," + h + "' fill='url(#" + gid + ")'/>" +
      "<polyline points='" + linea + "' fill='none' stroke='" + col + "' stroke-width='1.6' " +
      "stroke-linejoin='round' stroke-linecap='round'/></svg>";
  }
  function pintarSpark(el, s){
    // SVG EN LÍNEA (no <img> data-URI): se dibuja en el mismo frame, sin
    // decodificar imagen → al reemplazar el dibujo del servidor no hay parpadeo.
    var buf = spark[s];
    if (!buf || !buf.length) return;
    var t = ultimo[s];
    var col = (t && t.ch < 0) ? '#f85149' : '#3fb950';
    var clave = buf.length + '|' + buf[buf.length - 1] + '|' + buf[0] + '|' + col;
    if (el.getAttribute('data-pj-k') === clave) return;
    el.setAttribute('data-pj-k', clave);
    el.innerHTML = svgSpark(s, buf, col);
  }

