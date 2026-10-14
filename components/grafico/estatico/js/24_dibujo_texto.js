// [grafico] Dibujo: herramienta de texto
    var TAMANOS_TXT = [13, 16, 20, 26, 34];
    var editorTexto = null;

    var estiloTxt = document.createElement('style');
    estiloTxt.textContent = [
      '.tv-texto-input { position: absolute; z-index: 40; box-sizing: content-box; background: rgba(13,17,23,0.96); border: 1px dashed #58a6ff; border-radius: 4px; padding: 2px 4px; margin: 0; outline: none; font-family: sans-serif; }',
      '.sb-txt { background: transparent; border: 1px solid transparent; color: #8b949e; min-width: 28px; height: 26px; border-radius: 5px; cursor: pointer; padding: 0 4px; font-family: inherit; font-size: 12px; }',
      '.sb-txt:hover { background: rgba(255,255,255,0.08); color: #ffffff; }',
      '.sb-txt.on { background: rgba(88,166,255,0.18); color: #58a6ff; border-color: rgba(88,166,255,0.3); }'
    ].join(' ');
    document.head.appendChild(estiloTxt);

    function conTamanoTexto(el){ return el.tipo === 'text' || (typeof REG !== 'undefined' && REG[el.tipo] && REG[el.tipo].tamano); }
    function fuenteTexto(el){ return (el.negrita ? 'bold ' : '') + (el.tamano || 13) + 'px sans-serif'; }

    function cerrarEditorTexto(){
      if (editorTexto && editorTexto.parentNode) editorTexto.parentNode.removeChild(editorTexto);
      editorTexto = null;
    }

    function editarTexto(idx, pos, pt){
      cerrarEditorTexto();
      var el = (idx !== null) ? elementosDibujados[idx] : null;
      var sz = el ? (el.tamano || 13) : 13;
      var inp = document.createElement('input');
      inp.type = 'text';
      inp.className = 'tv-texto-input tv-ui';
      inp.value = el ? (el.texto || '') : '';
      inp.placeholder = 'Escribe y pulsa Enter';
      inp.style.fontSize = sz + 'px';
      if (el && el.negrita) inp.style.fontWeight = 'bold';
      inp.style.color = el ? (el.color || '#ffffff') : '#ffffff';
      inp.style.left = Math.round(pos.x - 5) + 'px';
      inp.style.top = Math.round(pos.y - sz - 6) + 'px';
      function ajustar(){
        ctx.font = (el && el.negrita ? 'bold ' : '') + sz + 'px sans-serif';
        inp.style.width = Math.max(140, Math.ceil(ctx.measureText(inp.value || inp.placeholder).width) + 16) + 'px';
      }
      ajustar();
      inp.addEventListener('input', ajustar);
      wrapEl.appendChild(inp);
      editorTexto = inp;
      var terminado = false;
      function cerrar(guardar){
        if (terminado) return;
        terminado = true;
        var valor = inp.value.trim();
        if (inp.parentNode) inp.parentNode.removeChild(inp);
        if (editorTexto === inp) editorTexto = null;
        if (!guardar || !valor) { redibujarTodo(); return; }
        if (el) {
          if (el.texto !== valor) { el.texto = valor; confirmarCambio(); } else { redibujarTodo(); }
        } else if (pt) {
          elementosDibujados.push({ tipo: 'text', time: pt.time, price: pt.price, texto: valor });
          seleccionadoId = elementosDibujados.length - 1;
          confirmarCambio();
        }
      }
      inp.addEventListener('keydown', function(e){
        e.stopPropagation();
        if (e.key === 'Enter') { e.preventDefault(); cerrar(true); }
        else if (e.key === 'Escape') { cerrar(false); }
      });
      inp.addEventListener('blur', function(){ cerrar(true); });
      setTimeout(function(){ inp.focus(); inp.select(); }, 0);
    }

    wrapEl.addEventListener('dblclick', function(e){
      if (bloqueado || activeTool !== 'cross') return;
      if (e.target && e.target.closest && e.target.closest('.tv-ui')) return;
      var pos = posMouse(e);
      var hit = elementoBajo(pos.x, pos.y);
      if (hit && elementosDibujados[hit.idx].tipo === 'text') {
        e.preventDefault(); e.stopPropagation();
        var g = geom(elementosDibujados[hit.idx]);
        seleccionadoId = hit.idx;
        redibujarTodo();
        if (typeof abrirAjustesDibujo === 'function') abrirAjustesDibujo(hit.idx); else editarTexto(hit.idx, { x: g.x, y: g.y });
      }
    }, true);

    var bloqueTexto = document.createElement('div');
    bloqueTexto.className = 'sb-bloque';
    bloqueTexto.style.display = 'none';
    TAMANOS_TXT.forEach(function(t){
      var b = document.createElement('button');
      b.className = 'sb-txt'; b.title = 'Tamaño ' + t + ' px'; b.setAttribute('data-tamano', String(t)); b.textContent = String(t);
      bloqueTexto.appendChild(b);
    });
    var btnNegrita = document.createElement('button');
    btnNegrita.className = 'sb-txt'; btnNegrita.title = 'Negrita'; btnNegrita.setAttribute('data-negrita', '1');
    btnNegrita.innerHTML = '<b>B</b>';
    bloqueTexto.appendChild(btnNegrita);
    barraEl.insertBefore(bloqueTexto, bloqueAcc);

    bloqueTexto.addEventListener('click', function(e){
      var btn = e.target.closest ? e.target.closest('button') : null;
      var el = elementoSeleccionado();
      if (!btn || !el || !conTamanoTexto(el)) return;
      if (btn.hasAttribute('data-tamano')) { el.tamano = parseInt(btn.getAttribute('data-tamano'), 10); }
      else if (btn.hasAttribute('data-negrita')) { el.negrita = !el.negrita; }
      else return;
      confirmarCambio();
      refrescarBarra(el);
    });

    var refrescarBarraBase = refrescarBarra;
    refrescarBarra = function(el){
      refrescarBarraBase(el);
      var esTxt = !!(el && conTamanoTexto(el));
      bloqueTexto.style.display = esTxt ? 'flex' : 'none';
      if (esTxt) {
        var t = el.tamano || 13, mejor = TAMANOS_TXT[0];
        TAMANOS_TXT.forEach(function(w){ if (Math.abs(w - t) < Math.abs(mejor - t)) mejor = w; });
        bloqueTexto.querySelectorAll('.sb-txt[data-tamano]').forEach(function(b){
          b.classList.toggle('on', parseInt(b.getAttribute('data-tamano'), 10) === mejor);
        });
        btnNegrita.classList.toggle('on', !!el.negrita);
      }
    };

