      function ubicar(){
        requestAnimationFrame(ubicar);
        if (!serie) return;
        var w = containerEl.clientWidth, h = containerEl.clientHeight;
        actualizarMercado();
        capa.style.left = containerEl.offsetLeft + 'px'; capa.style.top = containerEl.offsetTop + 'px';
        capa.style.width = w + 'px'; capa.style.height = h + 'px';
        var eje = 72;
        try { eje = chart.priceScale('right').width() || 72; } catch(e) {}
        var yLive = (BID && serie) ? serie.priceToCoordinate(BID) : null;   // y del recuadro blanco del precio en vivo
        var cajas = [];   // recuadros del eje visibles (para apilarlos sin pisar el blanco)
        if (ed){
          txt(ed.querySelector('.b'), BID ? fmt(BID, DIGITS) : '—');
          txt(ed.querySelector('.a'), ASK ? fmt(ASK, DIGITS) : '—');
          if (!ITEMS[edPrev ? edPrev.id : ''] && edPrev) cerrarEditor();   // la orden se ejecutó o se canceló
        }
        for (var id in nodos){
          var it = ITEMS[id], n = nodos[id];
          if (!it) continue;
          var lado = esCompra(it) ? COMPRA : VENTA;
          var arrPo = drag && drag.id === id && drag.f === 'po';
          var prev = edPrev && edPrev.id === id ? edPrev : null;
          var entrada = arrPo ? drag.px : (prev ? prev.po : precioEntrada(it, n));
          var y0 = serie.priceToCoordinate(entrada), visible;
          if (it.kind === 'pos'){
            visible = colocar(n.main, y0, w, h, eje, lado, (esCompra(it) ? '+' : '-') + fmt(it.v, 2),
                              pgTxt(it.p || 0), (it.p || 0) >= 0 ? COMPRA : VENTA, it.po, false, false);
            n.main.querySelector('.tg').title = TIPO[it.t] + ' ' + fmt(it.v, 2) + ' lote(s) a ' + fmt(it.po, DIGITS);
          } else {
            visible = colocar(n.main, y0, w, h, eje,
                              lado, TIPO[it.t].toUpperCase() + ' ' + fmt(it.v, 2) + (it.oco ? ' · OCO' : ''),
                              'at ' + fmt(entrada, DIGITS), '#c9d1d9', entrada, false, true);
          }
          var malPo = arrPo && validar(it, 'po', entrada, entrada);
          n.main.className = 'pl ' + (it.kind === 'ord' ? 'po' : 'pm') +
            ((n.pend.po !== undefined || n.pend.del) ? ' pend' : '') + (malPo ? ' mal' : '');
          if (visible) cajas.push({ej: n.main.querySelector('.ej'), y: y0});
          var ys = visible ? [y0] : [], hay = {};
          ['tp', 'sl'].forEach(function(f){
            var arrastra = drag && drag.id === id && drag.f === f;
            var px = arrastra ? drag.px : (prev ? prev[f] : (f in n.pend ? n.pend[f] : it[f]));
            var el = n[f];
            if (!px){ el.style.display = 'none'; return; }
            hay[f] = true;
            var col = f === 'tp' ? C_TP : C_SL, g = pgEn(it, entrada, px);
            var y = serie.priceToCoordinate(px);
            var etq = f.toUpperCase() + (f === 'sl' && it.tr ? ' auto' : '') + ' ' + fmt(it.v, 2);
            if (f === 'sl') el.querySelector('.x').title = it.tr
              ? 'Gestionado por el stop dinámico (quítalo en Cartera)' : 'Quitar Stop Loss';
            if (colocar(el, y, w, h, eje, col, etq, pgTxt(g),
                        g >= 0 ? COMPRA : VENTA, px, true, false)){ ys.push(y); cajas.push({ej: el.querySelector('.ej'), y: y}); }
            el.className = 'pl lv' + ((f in n.pend) ? ' pend' : '') +
                           (arrastra && validar(it, f, px, entrada) ? ' mal' : '');
          });
          // Insignias TP / SL (solo para los niveles que faltan)
          n.bdTp.style.display = hay.tp ? 'none' : '';
          n.bdSl.style.display = hay.sl ? 'none' : '';
          if (visible && (!hay.tp || !hay.sl) && !n.pend.del){
            n.bds.style.display = '';
            n.bds.style.top = (Math.round(y0) - 11) + 'px';
            n.bds.style.right = (eje + SEP + n.main.querySelector('.tg').offsetWidth + 6) + 'px';
          } else {
            n.bds.style.display = 'none';
          }
          // Conector vertical entre la línea principal y sus niveles (como XM)
          if (ys.length > 1){
            var a = Math.max(0, Math.min.apply(null, ys)), b = Math.min(h, Math.max.apply(null, ys));
            n.con.style.display = '';
            n.con.style.left = (w - eje - 14) + 'px';
            n.con.style.top = a + 'px'; n.con.style.height = (b - a) + 'px';
            n.con.style.borderLeftColor = lado; n.con.style.background = lado;
          } else {
            n.con.style.display = 'none';
          }
        }

        // ---- Apilado del eje (como XM): el recuadro BLANCO del precio en vivo MANDA
        // (se queda en su sitio) y EMPUJA los nuestros, que quedan PEGADOS (sin hueco).
        // Solo se mueve el chip del eje (.ej); la línea y la etiqueta grande siguen en su
        // precio real. Si no hay precio en vivo, cada recuadro queda en su sitio. ----
        var ALTO = 20;   // = alto del recuadro -> quedan pegados, sin espacio (todos iguales)
        var liveVivo = (yLive !== null && yLive >= 0 && yLive <= h - 10);
        if (liveVivo){
          liveEl.style.display = ''; liveEl.style.width = eje + 'px'; txt(liveEl, fmt(BID, DIGITS));
        } else {
          liveEl.style.display = 'none';
        }
        var lista = cajas.slice();
        if (liveVivo) lista.push({ej: liveEl, y: yLive, ancla: true, abs: true});   // el blanco es el ancla
        lista.sort(function(p, q){ return p.y - q.y; });
        var ia = -1;
        for (var i = 0; i < lista.length; i++){ if (lista[i].ancla){ ia = i; break; } }
        if (ia < 0){
          lista.forEach(function(c){ c.aj = c.y; });              // sin precio en vivo: sin empujar
        } else {
          lista[ia].aj = lista[ia].y;
          for (var i = ia - 1; i >= 0; i--){ lista[i].aj = Math.min(lista[i].y, lista[i + 1].aj - ALTO); }
          for (var i = ia + 1; i < lista.length; i++){ lista[i].aj = Math.max(lista[i].y, lista[i - 1].aj + ALTO); }
        }
        lista.forEach(function(c){
          if (!c.ej) return;
          c.ej.style.top = Math.round(c.abs ? c.aj - 10 : -10 + (c.aj - c.y)) + 'px';
        });
      }

