// [grafico] Comparar con otros símbolos (varias series superpuestas, en % sobre el mismo gráfico)
    // Como "Comparar o añadir símbolo" de XM/TradingView: cada símbolo se dibuja como una línea con su cierre y el
    // eje de precios pasa a porcentaje (todas las series parten de 0 % en la primera barra visible).
    // Los símbolos comparados se piden a la API con la misma temporalidad y número de barras que el gráfico principal
    // (/velas) y se actualizan cada pocos segundos (/ultima). La lista de símbolos sale de /simbolos (servidor_datos.py).
    var COLORES_CMP = ['#a855f7', '#f59e0b', '#06b6d4', '#ec4899', '#84cc16'];
    var MAX_CMP = 5;
    var comparados = [];            // { sym, color, serie, datos, error, req, elPct }
    var catalogoSimbolos = null;    // lista del servidor [{n, d, c}]; null = aún no disponible
    var catalogoEstado = '';        // '' | 'cargando' | 'sin_servidor'

    var modalCmp = document.getElementById('cmp-modal-overlay');
    var cmpInput = document.getElementById('cmp-search-input');
    var cmpLista = document.getElementById('cmp-list-container');
    var cmpMsg = document.getElementById('cmp-msg');

    function simboloValido(s){ return /^[A-Za-z0-9._#+\-]{1,24}$/.test(s); }
    function buscarCmp(sym){
      for (var i = 0; i < comparados.length; i++) if (comparados[i].sym.toUpperCase() === String(sym).toUpperCase()) return comparados[i];
      return null;
    }
    function colorLibreCmp(){
      var usados = comparados.map(function(c){ return c.color; });
      for (var i = 0; i < COLORES_CMP.length; i++) if (usados.indexOf(COLORES_CMP[i]) < 0) return COLORES_CMP[i];
      return COLORES_CMP[0];
    }

    // Eje en % mientras haya algo comparado; al volver a normal se recuperan los indicadores sobre el precio
    function aplicarModoComparar(){
      var activo = comparados.length > 0;
      var cambio = (activo !== modoComparar);
      modoComparar = activo;
      try {
        chart.priceScale('right').applyOptions({
          mode: activo ? LightweightCharts.PriceScaleMode.Percentage : LightweightCharts.PriceScaleMode.Normal
        });
      } catch (e) {}
      var b = document.getElementById('btn-cmp-select');
      if (b) {
        b.classList.toggle('activo', activo);
        var sp = b.querySelector('span');
        if (sp) sp.textContent = activo ? 'Comparar (' + comparados.length + ')' : 'Comparar';
      }
      if (cambio) actualizarIndicadoresActivos();
      redibujarTodo();
    }

    // Variación (%) de una serie entre la primera barra visible y la última
    function pctVisibleCmp(datos){
      if (!datos || !datos.length) return null;
      var r = null;
      try { r = chart.timeScale().getVisibleRange(); } catch (e) {}
      var i0 = 0;
      if (r && r.from !== undefined) { while (i0 < datos.length - 1 && datos[i0].time < r.from) i0++; }
      var base = datos[i0].close, ult = datos[datos.length - 1].close;
      return base ? (ult / base - 1) * 100 : null;
    }
    function actualizarPctCmp(){
      comparados.forEach(function(c){
        if (!c.elPct) return;
        if (c.error) { c.elPct.textContent = c.error; c.elPct.style.color = '#f85149'; return; }
        var p = pctVisibleCmp(c.datos);
        if (p === null) { c.elPct.textContent = '…'; c.elPct.style.color = '#8b949e'; return; }
        c.elPct.textContent = (p >= 0 ? '+' : '') + p.toFixed(2) + '%';
        c.elPct.style.color = p >= 0 ? '#3fb950' : '#f85149';
      });
    }
    function hayIndicadorSobrePrecio(){
      return ['sma20', 'sma50', 'sma200', 'ema20', 'ema50', 'bollinger', 'parabolic'].some(function(k){ return indicadores[k]; });
    }
    function refrescarLeyendaCmp(){
      var cont = document.getElementById('tv-cmp-legend');
      if (!cont) return;
      cont.innerHTML = '';
      comparados.forEach(function(c){
        var it = document.createElement('div'); it.className = 'cmp-item';
        var pto = document.createElement('span'); pto.className = 'cmp-pto'; pto.style.background = c.color;
        var nom = document.createElement('span'); nom.className = 'cmp-sym'; nom.textContent = c.sym;
        var pct = document.createElement('span'); pct.className = 'cmp-pct';
        var x = document.createElement('button'); x.className = 'cmp-x'; x.title = 'Quitar ' + c.sym; x.textContent = String.fromCharCode(10005);
        x.addEventListener('click', function(ev){ ev.stopPropagation(); quitarComparado(c); });
        it.appendChild(pto); it.appendChild(nom); it.appendChild(pct); it.appendChild(x);
        cont.appendChild(it);
        c.elPct = pct;
      });
      if (comparados.length && hayIndicadorSobrePrecio()) {
        var nota = document.createElement('div'); nota.className = 'cmp-nota';
        nota.textContent = 'Indicadores sobre el precio ocultos mientras compares';
        cont.appendChild(nota);
      }
      actualizarPctCmp();
    }

    function guardarSeleccionCmp(){
      listaCmpGuardada = comparados.map(function(c){ return c.sym; });
      guardarConfig();
      refrescarLeyendaCmp();
    }

    function cargarComparado(c){
      var miId = ++c.req, tf = tfActual, n = nBarrasActual;
      fetch(API + '/velas/' + encodeURIComponent(c.sym) + '?tf=' + tf + '&n=' + n)
        .then(function(r){ if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
        .then(function(v){
          if (miId !== c.req || comparados.indexOf(c) < 0) return;
          if (!Array.isArray(v) || !v.length) { c.error = 'sin datos'; c.datos = []; c.serie.setData([]); }
          else { c.error = ''; c.datos = v; c.serie.setData(v.map(function(p){ return { time: p.time, value: p.close }; })); }
          actualizarPctCmp(); redibujarTodo();
        })
        .catch(function(){
          if (miId !== c.req || comparados.indexOf(c) < 0) return;
          c.error = 'sin conexión'; actualizarPctCmp();
        });
    }
    function recargarComparados(){ comparados.forEach(cargarComparado); }

    // Devuelve '' si se añadió, o el motivo por el que no se pudo
    function agregarComparado(sym, sinGuardar){
      sym = String(sym || '').trim();
      if (!simboloValido(sym)) return 'Símbolo no válido.';
      if (sym.toUpperCase() === SIMBOLO.toUpperCase()) return 'Ese ya es el símbolo principal del gráfico.';
      if (buscarCmp(sym)) return 'Ya está en la comparación.';
      if (comparados.length >= MAX_CMP) return 'Máximo ' + MAX_CMP + ' símbolos comparados.';
      var color = colorLibreCmp();
      var serieC = chart.addLineSeries({
        color: color, lineWidth: 2, priceLineVisible: false, lastValueVisible: true, title: sym,
        priceFormat: { type: 'price', precision: 2, minMove: 0.01 }
      });
      var c = { sym: sym, color: color, serie: serieC, datos: [], error: '', req: 0, elPct: null };
      comparados.push(c);
      aplicarModoComparar();
      cargarComparado(c);
      if (sinGuardar) { listaCmpGuardada = comparados.map(function(x){ return x.sym; }); refrescarLeyendaCmp(); }
      else guardarSeleccionCmp();
      return '';
    }
    function quitarComparado(c){
      var i = comparados.indexOf(c);
      if (i < 0) return;
      comparados.splice(i, 1); c.req++;
      try { chart.removeSeries(c.serie); } catch (e) {}
      aplicarModoComparar();
      guardarSeleccionCmp();
    }

    // --- Ventana de búsqueda ---
    function mensajeCmp(t){ cmpMsg.textContent = t || ''; }
    function notaCmp(t){
      var d = document.createElement('div'); d.className = 'cmp-nota'; d.textContent = t; cmpLista.appendChild(d);
    }
    function renderizarListaCmp(filtro){
      cmpLista.innerHTML = '';
      if (catalogoEstado === 'cargando') { notaCmp('Cargando símbolos…'); return; }
      if (catalogoSimbolos === null) {
        notaCmp('No se pudo cargar la lista de símbolos (reinicia servidor_datos.py para activarla). Mientras tanto escribe el símbolo exacto y pulsa Enter.');
        return;
      }
      var f = String(filtro || '').trim().toLowerCase(), mostrados = 0;
      for (var i = 0; i < catalogoSimbolos.length && mostrados < 150; i++) {
        (function(it){
          var texto = (it.n + ' ' + (it.d || '') + ' ' + (it.c || '')).toLowerCase();
          if (f && texto.indexOf(f) < 0) return;
          mostrados++;
          var principal = it.n.toUpperCase() === SIMBOLO.toUpperCase();
          var c = buscarCmp(it.n);
          var fila = document.createElement('div'); fila.className = 'cmp-fila' + (principal ? ' deshab' : '');
          var txt = document.createElement('div'); txt.className = 'cmp-txt';
          var l1 = document.createElement('div');
          var nom = document.createElement('span'); nom.className = 'cmp-nom'; nom.textContent = it.n;
          l1.appendChild(nom);
          if (it.c) { var cat = document.createElement('span'); cat.className = 'cmp-cat'; cat.textContent = it.c; l1.appendChild(cat); }
          txt.appendChild(l1);
          if (it.d) { var de = document.createElement('div'); de.className = 'cmp-desc'; de.textContent = it.d; txt.appendChild(de); }
          var est = document.createElement('span'); est.className = 'cmp-estado' + (c ? ' on' : '');
          est.textContent = principal ? 'Principal' : (c ? 'Quitar' : 'Añadir');
          fila.appendChild(txt); fila.appendChild(est);
          if (!principal) fila.addEventListener('click', function(){
            var actual = buscarCmp(it.n);
            if (actual) { quitarComparado(actual); mensajeCmp(''); } else { mensajeCmp(agregarComparado(it.n)); }
            renderizarListaCmp(cmpInput.value);
          });
          cmpLista.appendChild(fila);
        })(catalogoSimbolos[i]);
      }
      if (!mostrados) notaCmp('Sin resultados. Pulsa Enter para intentar con «' + filtro + '».');
    }
    function cargarCatalogo(){
      if (catalogoSimbolos !== null || catalogoEstado === 'cargando') return;
      catalogoEstado = 'cargando'; renderizarListaCmp(cmpInput.value);
      fetch(API + '/simbolos')
        .then(function(r){ return r.json(); })
        .then(function(v){
          if (Array.isArray(v) && v.length) { catalogoSimbolos = v; catalogoEstado = ''; } else { catalogoEstado = 'sin_servidor'; }
          renderizarListaCmp(cmpInput.value);
        })
        .catch(function(){ catalogoEstado = 'sin_servidor'; renderizarListaCmp(cmpInput.value); });
    }
    function abrirModalCmp(){
      modalCmp.style.display = 'flex'; mensajeCmp(''); cmpInput.value = '';
      if (catalogoSimbolos === null) catalogoEstado = '';
      renderizarListaCmp('');
      cargarCatalogo();
      setTimeout(function(){ cmpInput.focus(); }, 50);
    }
    function cerrarModalCmp(){ modalCmp.style.display = 'none'; }

    document.getElementById('btn-cmp-select').addEventListener('click', function(e){ e.stopPropagation(); abrirModalCmp(); });
    document.getElementById('cmp-modal-close').addEventListener('click', cerrarModalCmp);
    modalCmp.addEventListener('click', function(e){ if (e.target === modalCmp) cerrarModalCmp(); });
    cmpInput.addEventListener('input', function(){ mensajeCmp(''); renderizarListaCmp(cmpInput.value); });
    cmpInput.addEventListener('keydown', function(e){
      if (e.key === 'Escape') { cerrarModalCmp(); return; }
      if (e.key !== 'Enter') return;
      var t = cmpInput.value.trim();
      if (!t) return;
      var exacto = (catalogoSimbolos || []).filter(function(it){ return it.n.toLowerCase() === t.toLowerCase(); })[0];
      mensajeCmp(agregarComparado(exacto ? exacto.n : t));
      renderizarListaCmp(cmpInput.value);
    });

    // El % de la leyenda sigue al zoom/desplazamiento (a lo sumo una vez por fotograma)
    var rafCmp = false;
    chart.timeScale().subscribeVisibleTimeRangeChange(function(){
      if (!comparados.length || rafCmp) return;
      rafCmp = true;
      requestAnimationFrame(function(){ rafCmp = false; actualizarPctCmp(); });
    });

    // Actualización en vivo de los símbolos comparados (el feed de ticks solo cubre los símbolos de la página)
    setInterval(function(){
      if (!comparados.length || document.hidden) return;
      comparados.forEach(function(c){
        if (!c.datos.length || c.error) return;
        var tf = tfActual, id = c.req;
        fetch(API + '/ultima/' + encodeURIComponent(c.sym) + '?tf=' + tf)
          .then(function(r){ return r.json(); })
          .then(function(v){
            if (tf !== tfActual || id !== c.req || !v || !v.time || comparados.indexOf(c) < 0) return;
            var ultima = c.datos[c.datos.length - 1];
            if (v.time < ultima.time) return;
            if (v.time === ultima.time) c.datos[c.datos.length - 1] = v; else c.datos.push(v);
            c.serie.update({ time: v.time, value: v.close });
            actualizarPctCmp();
          })
          .catch(function(){});
      });
    }, 6000);

    // Restaurar la comparación recordada (sin volver a guardar mientras se arma el gráfico)
    cfgComparar.forEach(function(s){ agregarComparado(s, true); });
