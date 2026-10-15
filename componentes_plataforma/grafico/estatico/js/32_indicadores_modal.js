// [grafico] Indicadores: ventana de selección y ventana de ajustes
    var modalOverlay = document.getElementById('ind-modal-overlay');
    var btnIndSelect = document.getElementById('btn-ind-select');
    var modalClose = document.getElementById('ind-modal-close');
    var searchInput = document.getElementById('ind-search-input');
    var tabsInd = document.getElementById('ind-tabs');
    var tabActiva = 'Todos';

    function cantidadDe(id){ return indActivos.filter(function(i){ return i.id === id; }).length; }

    function renderizarTabs(){
      var nombres = ['Todos'].concat(GRUPOS_IND).concat(['Activos']);
      tabsInd.innerHTML = '';
      nombres.forEach(function(n){
        var b = document.createElement('button'); b.className = 'ind-tab' + (n === tabActiva ? ' on' : '');
        b.textContent = n === 'Activos' ? 'Activos (' + indActivos.length + ')' : n;
        b.addEventListener('click', function(){ tabActiva = n; renderizarTabs(); renderizarListaIndicadores(searchInput.value); });
        tabsInd.appendChild(b);
      });
    }

    function filaIndicador(df){
      var n = cantidadDe(df.id);
      var fila = document.createElement('div'); fila.className = 'ind-fila'; fila.title = df.desc;
      var txt = document.createElement('div'); txt.className = 'ind-txt';
      var nom = document.createElement('span'); nom.className = 'ind-nom'; nom.textContent = df.nombre;
      var sub = document.createElement('span'); sub.className = 'ind-sub';
      sub.textContent = (df.destino === 'panel' ? 'Panel propio · ' : 'Sobre el precio · ') + df.desc;
      if (modoComparar && df.destino === 'precio') { sub.textContent += '  ·  ⚠ Oculto mientras haya símbolos comparados'; sub.style.color = '#d29922'; }
      txt.appendChild(nom); txt.appendChild(sub);
      var est = document.createElement('span'); est.className = 'ind-estado' + (n ? ' on' : '');
      est.textContent = n ? (n > 1 ? n + ' activos · +' : 'Activo · +') : 'Añadir';
      fila.appendChild(txt); fila.appendChild(est);
      fila.addEventListener('click', function(){ anadirIndicador(df.id); renderizarTabs(); renderizarListaIndicadores(searchInput.value); });
      return fila;
    }

    function filaInstancia(inst){
      var df = DEFS[inst.id];
      var fila = document.createElement('div'); fila.className = 'ind-fila';
      var txt = document.createElement('div'); txt.className = 'ind-txt';
      var nom = document.createElement('span'); nom.className = 'ind-nom'; nom.textContent = tituloInstancia(inst) + (inst.oculto ? '  (oculto)' : '');
      var sub = document.createElement('span'); sub.className = 'ind-sub'; sub.textContent = df.nombre;
      if (modoComparar && df.destino === 'precio') { sub.textContent += '  ·  ⚠ Oculto mientras compares'; sub.style.color = '#d29922'; }
      txt.appendChild(nom); txt.appendChild(sub);
      var acc = document.createElement('div'); acc.className = 'ind-acciones';
      function mini(t, titulo, fn, cls){
        var b = document.createElement('button'); b.className = 'ind-mini' + (cls ? ' ' + cls : ''); b.textContent = t; b.title = titulo;
        b.addEventListener('click', function(ev){ ev.stopPropagation(); fn(); });
        acc.appendChild(b);
      }
      mini(inst.oculto ? 'Mostrar' : 'Ocultar', 'Mostrar u ocultar', function(){ inst.oculto = !inst.oculto; cambioIndicadores(); renderizarTabs(); renderizarListaIndicadores(searchInput.value); });
      mini(String.fromCharCode(9881), 'Ajustes', function(){ abrirAjustesInd(inst.uid); });
      mini(String.fromCharCode(10005), 'Quitar', function(){ quitarIndicador(inst.uid); renderizarTabs(); renderizarListaIndicadores(searchInput.value); }, 'rojo');
      fila.appendChild(txt); fila.appendChild(acc);
      return fila;
    }

    function renderizarListaIndicadores(filtro){
      var cont = document.getElementById('ind-list-container');
      cont.innerHTML = '';
      var q = (filtro || '').toLowerCase().trim(), hay = false;
      if (tabActiva === 'Activos') {
        indActivos.forEach(function(inst){
          if (q && (tituloInstancia(inst) + DEFS[inst.id].nombre).toLowerCase().indexOf(q) < 0) return;
          cont.appendChild(filaInstancia(inst)); hay = true;
        });
        if (!hay) { var v = document.createElement('div'); v.className = 'ind-vacio'; v.textContent = 'No hay indicadores activos.'; cont.appendChild(v); }
        return;
      }
      GRUPOS_IND.forEach(function(g){
        if (tabActiva !== 'Todos' && tabActiva !== g) return;
        var items = LISTA_DEFS.filter(function(df){
          return df.grupo === g && (!q || (df.nombre + ' ' + df.corto + ' ' + df.desc + ' ' + df.grupo).toLowerCase().indexOf(q) >= 0);
        });
        if (!items.length) return;
        hay = true;
        if (tabActiva === 'Todos') { var h = document.createElement('div'); h.className = 'ind-grupo'; h.textContent = g; cont.appendChild(h); }
        items.forEach(function(df){ cont.appendChild(filaIndicador(df)); });
      });
      if (!hay) { var nv = document.createElement('div'); nv.className = 'ind-vacio'; nv.textContent = 'Ningún indicador coincide con la búsqueda.'; cont.appendChild(nv); }
    }

    function abrirModalIndicadores(){
      modalOverlay.style.display = 'flex';
      renderizarTabs();
      renderizarListaIndicadores(searchInput.value);
      setTimeout(function(){ searchInput.focus(); }, 50);
    }
    btnIndSelect.addEventListener('click', function(e){ e.stopPropagation(); abrirModalIndicadores(); });
    modalClose.addEventListener('click', function(){ modalOverlay.style.display = 'none'; });
    modalOverlay.addEventListener('click', function(e){ if (e.target === modalOverlay) modalOverlay.style.display = 'none'; });
    searchInput.addEventListener('input', function(e){ renderizarListaIndicadores(e.target.value); });

    // ---------- Ajustes de un indicador (Entradas de datos / Estilo / Visibilidad) ----------
    var cfgOverlay = document.getElementById('indcfg-overlay');
    var cfgCuerpo = document.getElementById('indcfg-cuerpo');
    var cfgTabs = document.getElementById('indcfg-tabs');
    var cfgUid = null, cfgSnap = null, cfgTab = 'entradas';

    function cerrarAjustes(){ cfgOverlay.style.display = 'none'; cfgUid = null; cfgSnap = null; }
    function cerrarAjustesSiEs(uid){ if (cfgUid === uid) cerrarAjustes(); }
    function instAjustes(){ return indActivos.filter(function(i){ return i.uid === cfgUid; })[0]; }
    function cancelarAjustes(){   // descarta lo cambiado desde que se abrió la ventana
      var inst = instAjustes();
      if (inst && cfgSnap) { restaurarInstancia(inst, cfgSnap); reconstruirIndicador(inst); }
      cerrarAjustes();
    }
    function aplicarCambio(inst){
      reconstruirIndicador(inst);
      document.getElementById('indcfg-titulo').textContent = tituloInstancia(inst) + '  ·  ' + DEFS[inst.id].nombre;
    }

    function el(tag, cls, txt){ var e = document.createElement(tag); if (cls) e.className = cls; if (txt !== undefined) e.textContent = txt; return e; }
    function fila(etiqueta, control){
      var f = el('div', 'cfg-fila'); f.appendChild(el('span', '', etiqueta)); f.appendChild(control); cfgCuerpo.appendChild(f);
    }
    function seccion(t){ cfgCuerpo.appendChild(el('div', 'cfg-sec', t)); }
    function selector(opciones, actual, alCambiar){
      var s = document.createElement('select');
      opciones.forEach(function(o){ var op = el('option', '', o[1]); op.value = o[0]; if (String(o[0]) === String(actual)) op.selected = true; s.appendChild(op); });
      s.addEventListener('change', function(){ alCambiar(s.value); });
      return s;
    }
    function casilla(texto, marcada, alCambiar){
      var l = el('label', 'cfg-check'); var c = document.createElement('input'); c.type = 'checkbox'; c.checked = marcada;
      c.addEventListener('change', function(){ alCambiar(c.checked); });
      l.appendChild(c); l.appendChild(el('span', '', texto)); return l;
    }
    function asegurarLista(inst, campo, n){
      if (!inst[campo]) inst[campo] = new Array(n).fill(null);
    }

    function pestanaEntradas(inst, df){
      if (!df.params.length) { cfgCuerpo.appendChild(el('div', 'cfg-vacio', 'Este indicador no tiene parámetros.')); return; }
      df.params.forEach(function(pd){
        var ctl;
        if (pd.t === 'sel') {
          ctl = selector(pd.o, inst.p[pd.k], function(v){ inst.p[pd.k] = valorParam(pd, v); aplicarCambio(inst); });
        } else {
          ctl = document.createElement('input'); ctl.type = 'number'; ctl.min = pd.min; ctl.max = pd.max; ctl.step = pd.paso; ctl.value = inst.p[pd.k];
          ctl.addEventListener('change', function(){ inst.p[pd.k] = valorParam(pd, ctl.value); ctl.value = inst.p[pd.k]; aplicarCambio(inst); });
        }
        fila(pd.n, ctl);
      });
    }

    var ESTILOS_LINEA = [[0, 'Sólida'], [2, 'Discontinua'], [1, 'Punteada']];
    function pestanaEstilo(inst, df){
      df.capas.forEach(function(cp, i){
        var tipo = cp[2] || 'linea';
        var f = el('div', 'cfg-fila cfg-estilo');
        f.appendChild(casilla(cp[0], capaVisible(inst, i), function(v){ asegurarLista(inst, 'v', df.capas.length); inst.v[i] = v ? null : 0; if (inst.v.every(function(x){ return x === null; })) inst.v = null; aplicarCambio(inst); }));
        var ctl = el('div', 'cfg-controles');
        var autoColor = (tipo === 'hist') && ['macd', 'osma', 'bulls', 'bears', 'ao', 'ac', 'gator', 'bwmfi', 'volumenes'].indexOf(df.id) >= 0;
        if (!autoColor) {
          var c = document.createElement('input'); c.type = 'color'; c.value = colorCapa(inst, i);
          c.addEventListener('input', function(){ asegurarLista(inst, 'c', df.capas.length); inst.c[i] = c.value; aplicarCambio(inst); });
          ctl.appendChild(c);
        }
        if (tipo === 'linea') {
          ctl.appendChild(selector(ESTILOS_LINEA, estiloLineaCapa(inst, i), function(v){ asegurarLista(inst, 's', df.capas.length); inst.s[i] = Number(v); aplicarCambio(inst); }));
          ctl.appendChild(selector([1, 2, 3, 4, 5].map(function(n){ return [n, n + ' px']; }), anchoCapa(inst, i), function(v){ asegurarLista(inst, 'w', df.capas.length); inst.w[i] = Number(v); aplicarCambio(inst); }));
        }
        f.appendChild(ctl); cfgCuerpo.appendChild(f);
      });
      seccion('Salidas');
      var precisiones = [['', 'Por defecto']].concat([0, 1, 2, 3, 4, 5, 6, 7, 8].map(function(n){ return [n, String(n) + (n === 1 ? ' decimal' : ' decimales')]; }));
      fila('Precisión', selector(precisiones, inst.pr === null ? '' : inst.pr, function(v){ inst.pr = (v === '') ? null : Number(v); aplicarCambio(inst); }));
      cfgCuerpo.appendChild(casilla('Etiquetas en la escala de precios', inst.et, function(v){ inst.et = v; aplicarCambio(inst); }));
      cfgCuerpo.appendChild(casilla('Valores en la línea de estado', inst.sl, function(v){ inst.sl = v; aplicarCambio(inst); }));
    }

    function pestanaVisibilidad(inst){
      GRUPOS_TF.forEach(function(g){
        var r = inst.vis[g[0]], f = el('div', 'cfg-vis');
        f.appendChild(casilla(g[1], r[0], function(v){ r[0] = v; aplicarCambio(inst); }));
        var mn = document.createElement('input'), mx = document.createElement('input');
        mn.type = mx.type = 'number'; mn.min = mx.min = g[2]; mn.max = mx.max = g[3]; mn.value = r[1]; mx.value = r[2];
        var dual = el('div', 'cfg-dual'), rmn = document.createElement('input'), rmx = document.createElement('input');
        rmn.type = rmx.type = 'range'; rmn.min = rmx.min = g[2]; rmn.max = rmx.max = g[3]; rmn.value = r[1]; rmx.value = r[2];
        dual.appendChild(rmn); dual.appendChild(rmx);
        function pintaPista(){
          var span = g[3] - g[2] || 1, a = (r[1] - g[2]) / span * 100, b = (r[2] - g[2]) / span * 100;
          dual.style.background = 'linear-gradient(to right,#3a3f47 ' + a + '%,#d1d4dc ' + a + '%,#d1d4dc ' + b + '%,#3a3f47 ' + b + '%)';
        }
        function fija(a, b, quien){
          a = Math.round(Number(a)); b = Math.round(Number(b));
          if (!isFinite(a)) a = r[1]; if (!isFinite(b)) b = r[2];
          a = Math.min(g[3], Math.max(g[2], a)); b = Math.min(g[3], Math.max(g[2], b));
          if (a > b) { if (quien === 'min') a = b; else b = a; }
          r[1] = a; r[2] = b; mn.value = rmn.value = a; mx.value = rmx.value = b; pintaPista(); aplicarCambio(inst);
        }
        mn.addEventListener('change', function(){ fija(mn.value, r[2], 'min'); });
        mx.addEventListener('change', function(){ fija(r[1], mx.value, 'max'); });
        rmn.addEventListener('input', function(){ fija(rmn.value, r[2], 'min'); });
        rmx.addEventListener('input', function(){ fija(r[1], rmx.value, 'max'); });
        pintaPista();
        f.appendChild(mn); f.appendChild(dual); f.appendChild(mx);
        cfgCuerpo.appendChild(f);
      });
      cfgCuerpo.appendChild(el('div', 'cfg-nota', 'El indicador solo se muestra en las temporalidades marcadas y dentro del rango indicado (p. ej. Minutos 1–15: M1, M5 y M15).'));
    }

    function pintarAjustes(){
      var inst = instAjustes();
      if (!inst) return;
      var df = DEFS[inst.id];
      document.getElementById('indcfg-titulo').textContent = tituloInstancia(inst) + '  ·  ' + df.nombre;
      cfgTabs.innerHTML = '';
      [['entradas', 'Entradas de datos'], ['estilo', 'Estilo'], ['visibilidad', 'Visibilidad']].forEach(function(tb){
        var b = el('button', 'cfg-tab' + (cfgTab === tb[0] ? ' on' : ''), tb[1]);
        b.addEventListener('click', function(){ cfgTab = tb[0]; pintarAjustes(); });
        cfgTabs.appendChild(b);
      });
      cfgCuerpo.innerHTML = '';
      if (cfgTab === 'entradas') pestanaEntradas(inst, df);
      else if (cfgTab === 'estilo') pestanaEstilo(inst, df);
      else pestanaVisibilidad(inst);
    }

    function abrirAjustesInd(uid){
      var inst = indActivos.filter(function(i){ return i.uid === uid; })[0];
      if (!inst) return;
      cfgUid = uid;
      cfgSnap = JSON.parse(JSON.stringify(serializarInstancia(inst)));
      cfgTab = 'entradas';
      pintarAjustes();
      cfgOverlay.style.display = 'flex';
    }

    document.getElementById('indcfg-close').addEventListener('click', cancelarAjustes);
    document.getElementById('indcfg-cancel').addEventListener('click', cancelarAjustes);
    document.getElementById('indcfg-ok').addEventListener('click', function(){ cambioIndicadores(); cerrarAjustes(); });
    document.getElementById('indcfg-reset').addEventListener('click', function(){
      var inst = instAjustes();
      if (!inst) return;
      restaurarInstancia(inst, { id: inst.id });
      reconstruirIndicador(inst);
      pintarAjustes();
    });
    cfgOverlay.addEventListener('click', function(e){ if (e.target === cfgOverlay) cancelarAjustes(); });
    document.addEventListener('keydown', function(e){
      if (e.key !== 'Escape') return;
      if (cfgOverlay.style.display !== 'none') cancelarAjustes();
      else if (modalOverlay.style.display !== 'none') modalOverlay.style.display = 'none';
    });
