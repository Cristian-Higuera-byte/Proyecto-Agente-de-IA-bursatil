      // ---------- Menú del clic derecho ----------
      function cerrarMenu(){ if (menu && menu.parentNode) menu.parentNode.removeChild(menu); menu = null; }
      containerEl.addEventListener('contextmenu', function(e){
        e.preventDefault();
        if (!serie) return;
        cerrarMenu();
        var r = containerEl.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
        var px = serie.coordinateToPrice(y);
        if (px === null) return;
        px = redondear(px);
        var vol = volumenTicket(), ops = [], oc = oneClick();
        if (BID && ASK){
          if (px < BID - SM) ops = [['Buy Limit', COMPRA, '▲'], ['Sell Stop', VENTA, '▼']];
          else if (px > ASK + SM) ops = [['Sell Limit', VENTA, '▼'], ['Buy Stop', COMPRA, '▲']];
        }
        menu = document.createElement('div'); menu.id = 'pj-menu';
        var h = '<div class="tit">' + REAL + ' · ' + fmt(px, DIGITS) + '</div>';
        if (ops.length){
          ops.forEach(function(o, i){
            h += '<div class="it" data-i="' + i + '"><span class="ic" style="color:' + o[1] + '">' + o[2] + '</span>' +
                 o[0] + ' ' + fmt(vol, 2) + '<span class="px">' + fmt(px, DIGITS) + '</span></div>';
          });
        } else {
          h += '<div class="it dis"><span class="ic">·</span>' + (BID ? 'Precio dentro del spread' : 'Sin precio en vivo') + '</div>';
        }
        h += '<div class="sep"></div><div class="it" data-oc="1"><span class="ic" style="color:#ff8f00">' +
             (oc ? '✓' : '⚡') + '</span>One-Click Trading<span class="px">' + (oc ? 'ON' : 'OFF') + '</span></div>';
        menu.innerHTML = h;
        menu.style.left = Math.max(0, Math.min(x, containerEl.clientWidth - 250)) + 'px';
        menu.style.top = Math.max(0, Math.min(y, containerEl.clientHeight - 150)) + 'px';
        menu.addEventListener('mousedown', function(ev){ ev.stopPropagation(); });
        menu.addEventListener('click', function(ev){
          var it = ev.target.closest('.it');
          if (!it || it.classList.contains('dis')) return;
          cerrarMenu();
          if (it.getAttribute('data-oc')){ alternarOneClick(); return; }
          nuevaOrden(ops[+it.getAttribute('data-i')][0], px);
        });
        capa.appendChild(menu);
      }, true);
      document.addEventListener('mousedown', function(){ cerrarMenu(); });

