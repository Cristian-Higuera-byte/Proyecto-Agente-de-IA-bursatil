      // ---------- Líneas ----------
      function crearLinea(clase){
        var el = document.createElement('div'); el.className = 'pl ' + clase;
        el.innerHTML = '<div class="ln"></div><div class="tg"><span class="vo"></span><span class="pg"></span>' +
                       '<span class="x">&#10005;</span></div><div class="ej"></div>';
        el.style.display = 'none';
        capa.appendChild(el);
        return el;
      }

      function empezar(id, f, e){
        if (e.button !== 0) return;
        if (f === 'sl' && ITEMS[id] && ITEMS[id].tr){
          e.preventDefault(); e.stopPropagation();
          avisar('El Stop Loss está en automático (stop dinámico). Para cambiarlo, edita la distancia en Cartera.', true);
          return;
        }
        e.preventDefault(); e.stopPropagation();
        cerrarMenu(); cerrarConf(true);
        drag = {id: id, f: f, px: null, y0: e.clientY, movido: false};
        document.body.style.cursor = 'ns-resize';
      }

      function crear(id){
        var it = ITEMS[id];
        var n = {main: crearLinea(it.kind === 'ord' ? 'po' : 'pm'), tp: crearLinea('lv'), sl: crearLinea('lv'), pend: {}};
        n.con = document.createElement('div'); n.con.className = 'cn'; capa.appendChild(n.con);
        n.bds = document.createElement('div'); n.bds.className = 'bds';
        n.bds.innerHTML = '<span class="bd" title="Arrastrar para añadir Take Profit">TP</span>' +
                          '<span class="bd" title="Arrastrar para añadir Stop Loss">SL</span>';
        capa.appendChild(n.bds);
        n.bdTp = n.bds.children[0]; n.bdSl = n.bds.children[1];
        n.bdTp.style.color = C_TP; n.bdTp.style.borderColor = C_TP;
        n.bdSl.style.color = C_SL; n.bdSl.style.borderColor = C_SL;
        n.bdTp.addEventListener('mousedown', function(e){ empezar(id, 'tp', e); });
        n.bdSl.addEventListener('mousedown', function(e){ empezar(id, 'sl', e); });
        var x = n.main.querySelector('.x');
        x.addEventListener('mousedown', function(e){ e.stopPropagation(); });
        if (it.kind === 'pos'){
          // ✕ de la posición → modal de cierre (botón invisible de Python, gatillos_cierre)
          x.title = 'Cerrar posición';
          x.addEventListener('click', function(e){
            e.stopPropagation();
            try { var b = PD.querySelector('.st-key-chcls_' + it.tk + ' button'); if (b) b.click(); } catch(err) {}
          });
        } else {
          x.title = 'Cancelar orden';
          x.addEventListener('click', function(e){ e.stopPropagation(); cancelarOrden(id); });
          var tgo = n.main.querySelector('.tg');
          tgo.title = 'Arrastrar para mover · doble clic o clic derecho para modificar';
          tgo.addEventListener('mousedown', function(e){ if (e.detail < 2) empezar(id, 'po', e); });
          tgo.addEventListener('dblclick', function(e){ e.stopPropagation(); drag = null; document.body.style.cursor = ''; abrirEditor(id); });
          tgo.addEventListener('contextmenu', function(e){ menuOrden(e, id); });
        }
        ['tp', 'sl'].forEach(function(f){
          var lv = n[f], lx = lv.querySelector('.x');
          lx.title = 'Quitar ' + NOMBRE[f];
          lx.addEventListener('mousedown', function(e){ e.stopPropagation(); });
          lx.addEventListener('click', function(e){
            e.stopPropagation();
            // SL en automático (stop dinámico): el motor lo repone enseguida, así que
            // quitarlo desde aquí no sirve (reaparece). Se bloquea como el arrastre.
            if (f === 'sl' && ITEMS[id] && ITEMS[id].tr){
              avisar('El Stop Loss está en automático (stop dinámico). Para quitarlo, desactiva el stop dinámico en Cartera.', true);
              return;
            }
            cambiarNivel(id, f, 0);
          });
          lv.querySelector('.tg').title = 'Arrastrar para mover el ' + NOMBRE[f];
          lv.querySelector('.tg').addEventListener('mousedown', function(e){ empezar(id, f, e); });
        });
        return n;
      }

      function borrar(id){
        var n = nodos[id];
        [n.main, n.tp, n.sl, n.con, n.bds].forEach(function(el){ if (el.parentNode) el.parentNode.removeChild(el); });
        delete nodos[id];
      }

      // Une posiciones y órdenes en ITEMS y crea/borra sus líneas
      function unir(){
        var nuevo = {};
        for (var a in POS){ POS[a].kind = 'pos'; POS[a].tk = a; nuevo['p' + a] = POS[a]; }
        for (var b in ORD){ ORD[b].kind = 'ord'; ORD[b].tk = b; nuevo['o' + b] = ORD[b]; }
        ITEMS = nuevo;
        for (var id in nodos){ if (!ITEMS[id]) borrar(id); }
        for (var id2 in ITEMS){ if (!nodos[id2]) nodos[id2] = crear(id2); }
      }

      function mover(e){
        if (!drag || !serie) return;
        if (!drag.movido && Math.abs(e.clientY - drag.y0) < 4) return;   // un clic no es un arrastre
        drag.movido = true;
        var r = containerEl.getBoundingClientRect();
        var px = serie.coordinateToPrice(e.clientY - r.top);
        if (px !== null) drag.px = redondear(px);
      }
      function soltar(cancelar){
        if (!drag) return;
        var d = drag; drag = null;
        document.body.style.cursor = '';
        var it = ITEMS[d.id];
        if (cancelar || !it || d.px === null || !d.movido) return;
        var actual = d.f === 'po' ? precioEntrada(it, nodos[d.id]) : (+it[d.f] || 0);
        if (redondear(actual) === d.px) return;                          // mismo precio: nada que enviar
        var motivo = validar(it, d.f, d.px, precioEntrada(it, nodos[d.id]));
        if (motivo){ avisar('No válido: ' + motivo, true); return; }
        cambiarNivel(d.id, d.f, d.px);
      }
      document.addEventListener('mousemove', function(e){
        if (!drag) return;
        if (e.buttons === 0){ soltar(true); return; }   // se soltó fuera del gráfico
        mover(e);
      });
      document.addEventListener('mouseup', function(){ soltar(false); });
      document.addEventListener('keydown', function(e){
        if (e.key === 'Escape'){ soltar(true); cerrarMenu(); cerrarConf(true); cerrarEditor(); }
      });

      // Dibuja una línea en la altura del precio dado
      function colocar(el, y, w, h, eje, col, vo, pg, pgCol, pxEje, nivel, esOrden){
        if (y === null || y < 0 || y > h - 28){ el.style.display = 'none'; return false; }
        el.style.display = '';
        el.style.top = Math.round(y) + 'px';
        el.style.width = w + 'px';
        var ln = el.querySelector('.ln'), v = el.querySelector('.vo'), g = el.querySelector('.pg'),
            x = el.querySelector('.x'), ej = el.querySelector('.ej'), tg = el.querySelector('.tg');
        // ORDEN PENDIENTE: borde punteado en etiqueta y recuadro (como su línea), relleno intacto.
        var ord = esOrden && !nivel, bs = ord ? 'dashed' : 'solid';
        ln.style.width = (w - eje) + 'px';
        ln.style.borderTopColor = col;
        tg.style.right = (eje + SEP) + 'px';
        txt(v, vo);
        if (nivel){ v.style.background = '#161b22'; v.style.color = col; v.style.borderColor = col; }
        else { v.style.background = col; v.style.color = '#fff';
               v.style.borderColor = ord ? '#0d1117' : col; }   // punteado oscuro visible sobre el relleno
        v.style.borderStyle = bs;
        txt(g, pg);
        g.style.color = pgCol;
        g.style.borderColor = col; g.style.borderStyle = bs;
        x.style.borderColor = col; x.style.borderLeftColor = '#30363d'; x.style.borderStyle = bs;
        // Recuadro del eje: posiciones/órdenes RELLENO; niveles TP/SL solo CONTORNO
        // (como XM: así el TP/SL no se confunde con una posición). Las órdenes pendientes
        // llevan el borde punteado para distinguirse de las posiciones abiertas.
        ej.style.width = eje + 'px';
        if (nivel){ ej.style.background = '#0d1117'; ej.style.color = col;
                    ej.style.boxShadow = 'inset 0 0 0 1.5px ' + col; ej.style.border = 'none'; }
        else { ej.style.background = col; ej.style.color = '#fff'; ej.style.boxShadow = 'none';
               ej.style.border = ord ? '1.5px dashed #0d1117' : 'none'; }
        txt(ej, fmt(pxEje, DIGITS));
        return true;
      }
      function pgTxt(v){ return (v >= 0 ? '+' : '') + fmt(v, 2) + ' USD'; }

      // Cada frame: alturas (zoom, desplazamiento, autoescala) y arrastres
