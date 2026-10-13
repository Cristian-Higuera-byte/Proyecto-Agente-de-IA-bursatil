// [grafico] Dibujo: barra de estilos, copiar/pegar, ocultar y bloquear
    var dibujosVisibles = true;
    var portapapeles = null;

    var PALETA_DIB = ['#2962ff', '#58a6ff', '#089981', '#3fb950', '#f5c518', '#ff9800', '#f23645', '#a78bfa', '#ffffff'];
    var ANCHOS_DIB = [1, 2, 3, 4];
    var COLOR_DEF = { trend: '#2962ff', ray: '#2962ff', extended: '#2962ff', angle: '#a78bfa', hline: '#f5c518',
      hray: '#f5c518', vline: '#58a6ff', crossline: '#8b949e', channel: '#2962ff', rectangle: '#58a6ff',
      ellipse: '#58a6ff', triangle: '#58a6ff', arrow: '#3fb950', text: '#ffffff', brush: '#ff9800', highlighter: 'rgba(255,235,59,0.35)' };
    var ANCHO_DEF = { hline: 1.5, hray: 1.5, vline: 1.5, crossline: 1, brush: 3, highlighter: 18 };
    var ESTILO_DEF = { hline: 'dash', vline: 'dash', crossline: 'dash' };
    var TIPOS_TRAZO = { trend: 1, ray: 1, extended: 1, angle: 1, hline: 1, hray: 1, vline: 1, crossline: 1, channel: 1, arrow: 1 };
    var TIPOS_ANCHO = { trend: 1, ray: 1, extended: 1, angle: 1, hline: 1, hray: 1, vline: 1, crossline: 1, channel: 1, arrow: 1,
      rectangle: 1, ellipse: 1, triangle: 1, brush: 1, highlighter: 1 };
    var TIPOS_COLOR = { trend: 1, ray: 1, extended: 1, angle: 1, hline: 1, hray: 1, vline: 1, crossline: 1, channel: 1, arrow: 1,
      rectangle: 1, ellipse: 1, triangle: 1, text: 1, brush: 1, highlighter: 1 };

    var estiloUI2 = document.createElement('style');
    estiloUI2.textContent = [
      '.tvtool.on { background: rgba(139,92,246,0.18); color: #a78bfa; }',
      '#tv-stylebar { position: absolute; top: 10px; left: calc(50% + 22px); transform: translateX(-50%); z-index: 30; display: none; align-items: center; background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 5px 8px; box-shadow: 0 6px 20px rgba(0,0,0,0.5); user-select: none; font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; }',
      '#tv-stylebar.show { display: flex; }',
      '#tv-stylebar .sb-bloque { display: flex; align-items: center; gap: 3px; padding-right: 8px; margin-right: 8px; border-right: 1px solid #30363d; }',
      '#tv-stylebar .sb-bloque.ultimo { border-right: none; margin-right: 0; padding-right: 0; }',
      '.sb-color { width: 18px; height: 18px; border-radius: 50%; border: 2px solid transparent; cursor: pointer; padding: 0; }',
      '.sb-color.on { border-color: #ffffff; }',
      '.sb-ancho, .sb-estilo, .sb-btn { background: transparent; border: 1px solid transparent; color: #8b949e; width: 30px; height: 26px; border-radius: 5px; cursor: pointer; display: flex; align-items: center; justify-content: center; padding: 0; }',
      '.sb-ancho.on, .sb-estilo.on { background: rgba(88,166,255,0.18); color: #58a6ff; border-color: rgba(88,166,255,0.3); }',
      '.sb-btn:hover { background: rgba(255,255,255,0.08); color: #ffffff; }',
      '.sb-btn.peligro:hover { color: #f85149; }',
      '.sb-btn svg { width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-width: 1.6; stroke-linecap: round; stroke-linejoin: round; }',
      '#tv-stylebar input[type=color] { width: 22px; height: 22px; border: none; padding: 0; background: none; cursor: pointer; }',
      '#tv-actions .tvbtn[disabled] { opacity: 0.35; cursor: default; }'
    ].join(' ');
    document.head.appendChild(estiloUI2);

    function valorEfectivo(el, k){
      if (el[k] !== undefined && el[k] !== null) return el[k];
      if (k === 'color') return COLOR_DEF[el.tipo] || '#2962ff';
      if (k === 'ancho') return ANCHO_DEF[el.tipo] || 2;
      return ESTILO_DEF[el.tipo] || 'solid';
    }

    var areaDibEl = document.getElementById('tv-main-canvas-area');
    var barraEl = document.createElement('div');
    barraEl.id = 'tv-stylebar';

    var bloqueColor = document.createElement('div'); bloqueColor.className = 'sb-bloque';
    PALETA_DIB.forEach(function(col){
      var b = document.createElement('button');
      b.className = 'sb-color'; b.title = 'Color'; b.setAttribute('data-color', col); b.style.background = col;
      bloqueColor.appendChild(b);
    });
    var pickerEl = document.createElement('input');
    pickerEl.type = 'color'; pickerEl.title = 'Color personalizado'; pickerEl.value = '#2962ff';
    bloqueColor.appendChild(pickerEl);

    var bloqueAncho = document.createElement('div'); bloqueAncho.className = 'sb-bloque';
    ANCHOS_DIB.forEach(function(a){
      var b = document.createElement('button');
      b.className = 'sb-ancho'; b.title = 'Grosor ' + a + ' px'; b.setAttribute('data-ancho', String(a));
      b.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18"><path d="M3 12h18" stroke="currentColor" stroke-width="' + a + '" fill="none"/></svg>';
      bloqueAncho.appendChild(b);
    });

    var bloqueEstilo = document.createElement('div'); bloqueEstilo.className = 'sb-bloque';
    [['solid', '', 'Línea continua'], ['dash', '6 4', 'Línea discontinua'], ['dot', '1.5 3.5', 'Línea punteada']].forEach(function(par){
      var b = document.createElement('button');
      b.className = 'sb-estilo'; b.title = par[2]; b.setAttribute('data-estilo', par[0]);
      b.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18"><path d="M2 12h20" stroke="currentColor" stroke-width="2" fill="none" stroke-dasharray="' + par[1] + '"/></svg>';
      bloqueEstilo.appendChild(b);
    });

    var bloqueAcc = document.createElement('div'); bloqueAcc.className = 'sb-bloque ultimo';
    var bDup = document.createElement('button');
    bDup.className = 'sb-btn'; bDup.title = 'Duplicar'; bDup.setAttribute('data-accion', 'duplicar');
    bDup.innerHTML = '<svg viewBox="0 0 24 24"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a2 2 0 0 1 2-2h8"/></svg>';
    var bDel = document.createElement('button');
    bDel.className = 'sb-btn peligro'; bDel.title = 'Eliminar'; bDel.setAttribute('data-accion', 'borrar');
    bDel.innerHTML = '<svg viewBox="0 0 24 24"><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/></svg>';
    bloqueAcc.appendChild(bDup); bloqueAcc.appendChild(bDel);

    barraEl.appendChild(bloqueColor); barraEl.appendChild(bloqueAncho);
    barraEl.appendChild(bloqueEstilo); barraEl.appendChild(bloqueAcc);
    areaDibEl.appendChild(barraEl);

    function elementoSeleccionado(){
      return (seleccionadoId !== null && !bloqueado && dibujosVisibles) ? (elementosDibujados[seleccionadoId] || null) : null;
    }

    function refrescarBarra(el){
      if (!el) { barraEl.classList.remove('show'); return; }
      barraEl.classList.add('show');
      var t = el.tipo;
      bloqueColor.style.display = TIPOS_COLOR[t] ? 'flex' : 'none';
      bloqueAncho.style.display = TIPOS_ANCHO[t] ? 'flex' : 'none';
      bloqueEstilo.style.display = TIPOS_TRAZO[t] ? 'flex' : 'none';
      if (TIPOS_COLOR[t]) {
        var col = valorEfectivo(el, 'color');
        bloqueColor.querySelectorAll('.sb-color').forEach(function(b){
          b.classList.toggle('on', b.getAttribute('data-color') === col);
        });
        if (/^#[0-9a-fA-F]{6}$/.test(col)) pickerEl.value = col;
      }
      if (TIPOS_ANCHO[t]) {
        var a = valorEfectivo(el, 'ancho'), mejor = ANCHOS_DIB[0];
        ANCHOS_DIB.forEach(function(w){ if (Math.abs(w - a) < Math.abs(mejor - a)) mejor = w; });
        bloqueAncho.querySelectorAll('.sb-ancho').forEach(function(b){
          b.classList.toggle('on', parseFloat(b.getAttribute('data-ancho')) === mejor);
        });
      }
      if (TIPOS_TRAZO[t]) {
        var est = valorEfectivo(el, 'estilo');
        bloqueEstilo.querySelectorAll('.sb-estilo').forEach(function(b){
          b.classList.toggle('on', b.getAttribute('data-estilo') === est);
        });
      }
    }

    barraEl.addEventListener('click', function(e){
      var btn = e.target.closest ? e.target.closest('button') : null;
      var el = elementoSeleccionado();
      if (!btn || !el) return;
      if (btn.hasAttribute('data-color')) { el.color = btn.getAttribute('data-color'); }
      else if (btn.hasAttribute('data-ancho')) { el.ancho = parseFloat(btn.getAttribute('data-ancho')); }
      else if (btn.hasAttribute('data-estilo')) { el.estilo = btn.getAttribute('data-estilo'); }
      else if (btn.getAttribute('data-accion') === 'borrar') { borrarSeleccionado(); return; }
      else if (btn.getAttribute('data-accion') === 'duplicar') { copiarSeleccionado(); pegar(); return; }
      else return;
      confirmarCambio();
      refrescarBarra(el);
    });
    pickerEl.addEventListener('input', function(){
      var el = elementoSeleccionado();
      if (!el) return;
      el.color = pickerEl.value;
      redibujarTodo();
    });
    pickerEl.addEventListener('change', function(){
      var el = elementoSeleccionado();
      if (!el) return;
      confirmarCambio();
      refrescarBarra(el);
    });

    function borrarSeleccionado(){
      if (seleccionadoId === null || bloqueado) return;
      elementosDibujados.splice(seleccionadoId, 1);
      seleccionadoId = null; hoverId = null;
      confirmarCambio();
    }

    function copiarSeleccionado(){
      var el = elementoSeleccionado();
      if (el) portapapeles = JSON.stringify(el);
    }

    function pegar(){
      if (!portapapeles || bloqueado || !serie) return;
      var el = JSON.parse(portapapeles);
      var clavesT = [], clavesP = [];
      Object.keys(el).forEach(function(k){
        if (/^time[0-9]?$/.test(k) && typeof el[k] === 'number') clavesT.push(k);
        if (/^price[0-9]?$/.test(k) && typeof el[k] === 'number') clavesP.push(k);
      });
      clavesT.forEach(function(k){
        var l = tiempoALogico(el[k]);
        if (l !== null) el[k] = logicoATiempo(l + 4);
      });
      if (clavesP.length) {
        var yRef = yDePrecio(el[clavesP[0]]);
        var pDesp = ok(yRef) ? serie.coordinateToPrice(yRef + 24) : null;
        if (pDesp !== null) {
          var dp = pDesp - el[clavesP[0]];
          clavesP.forEach(function(k){ el[k] = el[k] + dp; });
        }
      }
      elementosDibujados.push(el);
      seleccionadoId = elementosDibujados.length - 1;
      confirmarCambio();
    }

    function botonIcono(interior, titulo, fn){
      var b = document.createElement('button');
      b.className = 'tvbtn icon'; b.title = titulo;
      b.innerHTML = '<svg viewBox="0 0 20 20">' + interior + '</svg>';
      b.addEventListener('click', fn);
      return b;
    }
    var accionesEl = document.getElementById('tv-actions');
    var btnUndo = botonIcono('<path d="M7 5L3.5 8.5 7 12"/><path d="M3.5 8.5H12a4 4 0 0 1 0 8H9"/>', 'Deshacer', function(){ deshacer(); });
    var btnRedo = botonIcono('<path d="M13 5l3.5 3.5L13 12"/><path d="M16.5 8.5H8a4 4 0 0 0 0 8h3"/>', 'Rehacer', function(){ rehacer(); });
    accionesEl.insertBefore(btnRedo, accionesEl.firstChild);
    accionesEl.insertBefore(btnUndo, btnRedo);

    var dibujosVisibles = true;
    var btnOcultar = document.createElement('button');
    btnOcultar.className = 'tvtool';
    var ICONO_OJO = '<svg viewBox="0 0 20 20"><path d="M2 10s3-5.5 8-5.5S18 10 18 10s-3 5.5-8 5.5S2 10 2 10z"/><circle cx="10" cy="10" r="2.4"/></svg>';
    var ICONO_OJO_OFF = '<svg viewBox="0 0 20 20"><path d="M2 10s3-5.5 8-5.5S18 10 18 10s-3 5.5-8 5.5S2 10 2 10z"/><circle cx="10" cy="10" r="2.4"/><path d="M3 3l14 14"/></svg>';
    function refrescarOcultar(){
      btnOcultar.innerHTML = dibujosVisibles ? ICONO_OJO : ICONO_OJO_OFF;
      btnOcultar.title = dibujosVisibles ? 'Ocultar dibujos' : 'Mostrar dibujos';
      btnOcultar.classList.toggle('on', !dibujosVisibles);
    }
    refrescarOcultar();
    var btnLockRef = document.getElementById('tool-lock');
    btnLockRef.parentNode.insertBefore(btnOcultar, btnLockRef);
    btnOcultar.addEventListener('click', function(e){
      e.stopPropagation();
      dibujosVisibles = !dibujosVisibles;
      if (!dibujosVisibles) { cancelarDibujoEnCurso(); activarHerramienta('cross'); seleccionadoId = null; hoverId = null; }
      refrescarOcultar();
      redibujarTodo();
    });

    var pintarOriginal = pintar;
    pintar = function(){
      if (!dibujosVisibles) { ctx.clearRect(0, 0, cssW, cssH); return; }
      pintarOriginal();
    };
    var elementoBajoOriginal = elementoBajo;
    elementoBajo = function(x, y){ return dibujosVisibles ? elementoBajoOriginal(x, y) : null; };
    var activarHerramientaOriginal = activarHerramienta;
    activarHerramienta = function(t){
      if (t !== 'cross' && !dibujosVisibles) { dibujosVisibles = true; refrescarOcultar(); redibujarTodo(); }
      activarHerramientaOriginal(t);
    };

    var vigSel = -2, vigObj = null, vigHist = '';
    function vigilarUI(){
      var el = elementoSeleccionado();
      if (seleccionadoId !== vigSel || el !== vigObj) { vigSel = seleccionadoId; vigObj = el; refrescarBarra(el); }
      var h = posHist + '/' + historial.length;
      if (h !== vigHist) {
        vigHist = h;
        btnUndo.disabled = posHist <= 0;
        btnRedo.disabled = posHist >= historial.length - 1;
      }
      requestAnimationFrame(vigilarUI);
    }
    requestAnimationFrame(vigilarUI);

    document.addEventListener('keydown', function(e){
      var tag = (e.target && e.target.tagName) || '';
      if (tag === 'INPUT' || tag === 'TEXTAREA') return;
      if (e.ctrlKey || e.metaKey) {
        var kl = (e.key || '').toLowerCase();
        if (kl === 'c') copiarSeleccionado();
        else if (kl === 'v') pegar();
        return;
      }
      if (e.altKey) {
        var mapa = { KeyT: 'trend', KeyH: 'hline', KeyV: 'vline', KeyF: 'fib', KeyB: 'brush' };
        var t = mapa[e.code];
        if (t) {
          e.preventDefault();
          var item = document.querySelector('.tvtool-flyout-item[data-tool="' + t + '"]');
          if (item) item.click(); else activarHerramienta(t);
        }
      }
    });

