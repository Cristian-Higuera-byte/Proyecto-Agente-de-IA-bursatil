      // ---------- Ventana "Modificar orden" (como MT5): doble clic o clic derecho en la línea ----------
      var ed = null, edPrev = null;
      function aLocal(exServidor){            // hora del servidor (s) -> valor de datetime-local
        var d = new Date((exServidor - OFF) * 1000), z = function(n){ return (n < 10 ? '0' : '') + n; };
        return d.getFullYear() + '-' + z(d.getMonth() + 1) + '-' + z(d.getDate()) + 'T' + z(d.getHours()) + ':' + z(d.getMinutes());
      }
      function aServidor(valorLocal){         // datetime-local -> hora del servidor (s)
        var t = new Date(valorLocal).getTime();
        return isNaN(t) ? 0 : Math.round(t / 1000 + OFF);
      }
      function cerrarEditor(){
        if (ed && ed.parentNode) ed.parentNode.removeChild(ed);
        ed = null; edPrev = null;
      }
      function menuOrden(e, id){
        e.preventDefault(); e.stopPropagation();
        cerrarMenu();
        var it = ITEMS[id]; if (!it) return;
        var r = containerEl.getBoundingClientRect();
        menu = document.createElement('div'); menu.id = 'pj-menu';
        var nom = '#' + it.tk + ' ' + TIPO[it.t].toLowerCase() + ' ' + fmt(it.v, 2);
        menu.innerHTML = '<div class="it" data-a="mod"><span class="ic" style="color:#58a6ff">&#9881;</span>Modificar ' + nom +
          '<span class="px">' + fmt(it.po, DIGITS) + '</span></div>' +
          '<div class="it" data-a="del"><span class="ic" style="color:#f85149">&#10005;</span>Eliminar ' + nom +
          '<span class="px">' + fmt(it.po, DIGITS) + '</span></div>';
        menu.style.left = Math.max(0, Math.min(e.clientX - r.left, containerEl.clientWidth - 330)) + 'px';
        menu.style.top = Math.max(0, Math.min(e.clientY - r.top, containerEl.clientHeight - 90)) + 'px';
        menu.addEventListener('mousedown', function(ev){ ev.stopPropagation(); });
        menu.addEventListener('click', function(ev){
          var x = ev.target.closest('.it'); if (!x) return;
          cerrarMenu();
          if (x.getAttribute('data-a') === 'mod') abrirEditor(id); else cancelarOrden(id);
        });
        capa.appendChild(menu);
      }
      function abrirEditor(id){
        cerrarMenu(); cerrarConf(true); cerrarEditor();
        var it = ITEMS[id];
        if (!it || it.kind !== 'ord') return;
        var paso = Math.pow(10, -DIGITS);
        ed = document.createElement('div'); ed.id = 'pj-ed';
        ed.innerHTML =
          '<div class="hd"><span class="tt"></span><span class="cx" title="Cerrar">&#10005;</span></div>' +
          '<div class="cuerpo"><div class="campos">' +
            '<label>Precio</label><input class="i-po" type="number" step="' + paso + '">' +
            '<label>Stop Loss</label><input class="i-sl" type="number" step="' + paso + '" min="0">' +
            '<label>Take Profit</label><input class="i-tp" type="number" step="' + paso + '" min="0">' +
            '<label>Caducidad</label><select class="i-tt"><option value="gtc">Good till cancelled (GTC)</option>' +
              '<option value="day">Day</option><option value="specified">Specified (fecha)</option></select>' +
            '<label class="l-ex">Fecha caducidad</label><input class="i-ex" type="datetime-local">' +
          '</div><div class="cot">' +
            '<div class="fila"><span class="k">Bid</span><span class="v b" style="color:' + VENTA + '"></span></div>' +
            '<div class="fila"><span class="k">Ask</span><span class="v a" style="color:' + COMPRA + '"></span></div>' +
            '<div class="proy"></div></div></div>' +
          '<div class="msg"></div>' +
          '<div class="bs"><button class="ok">Modificar</button><button class="del">Eliminar</button></div>' +
          '<div class="nt">El precio de entrada debe ' + (SM > 0 ? 'estar al menos a ' + fmt(SM, DIGITS) + ' del' : 'ser distinto del') +
          ' precio de mercado; lo mismo para Stop Loss y Take Profit. 0 = sin Stop Loss / Take Profit.</div>';
        ed.querySelector('.tt').textContent = 'Modificar orden #' + it.tk + ' · ' + TIPO[it.t] + ' ' + fmt(it.v, 2) + ' ' + REAL;
        var q = function(c){ return ed.querySelector(c); };
        q('.i-po').value = (+it.po).toFixed(DIGITS);
        q('.i-sl').value = (+it.sl || 0).toFixed(DIGITS);
        q('.i-tp').value = (+it.tp || 0).toFixed(DIGITS);
        var cad = ['gtc', 'day', 'specified'][it.tt || 0] || 'gtc';
        q('.i-tt').value = cad;
        [['gtc', 1], ['day', 2], ['specified', 4]].forEach(function(m){       // modos que admite el bróker
          if (EM && !(EM & m[1])) q('.i-tt option[value="' + m[0] + '"]').disabled = true;
        });
        q('.i-ex').value = aLocal(it.ex ? it.ex : Math.round(Date.now() / 1000 + OFF + 86400));
        var exIni = q('.i-ex').value;
        function leer(){
          return {po: parseFloat(q('.i-po').value), sl: parseFloat(q('.i-sl').value) || 0,
                  tp: parseFloat(q('.i-tp').value) || 0, tt: q('.i-tt').value, ex: q('.i-ex').value};
        }
        function revisar(){
          if (!ed) return;
          var v = leer(), err = '';
          var fecha = v.tt === 'specified';
          q('.i-ex').disabled = !fecha; q('.l-ex').style.opacity = fecha ? 1 : .45;
          if (isNaN(v.po) || v.po <= 0) err = 'Precio inválido';
          else err = validar(it, 'po', v.po, v.po) || (v.sl > 0 && validar(it, 'sl', v.sl, v.po)) ||
                     (v.tp > 0 && validar(it, 'tp', v.tp, v.po)) || '';
          if (!err && fecha && aServidor(v.ex) <= Date.now() / 1000 + OFF) err = 'la fecha de caducidad debe ser futura';
          var cambio = redondear(v.po) !== redondear(it.po) || redondear(v.sl) !== redondear(+it.sl || 0) ||
                       redondear(v.tp) !== redondear(+it.tp || 0) || v.tt !== cad || (fecha && v.ex !== exIni);
          q('.ok').disabled = !!err || !cambio;
          q('.msg').textContent = err ? 'No válido: ' + err : '';
          edPrev = isNaN(v.po) ? null : {id: id, po: v.po, sl: v.sl, tp: v.tp};
          var g = v.tp > 0 ? pgEn(it, v.po, v.tp) : null, l = v.sl > 0 ? pgEn(it, v.po, v.sl) : null;
          q('.proy').innerHTML = (g !== null ? '<span style="color:' + C_TP + '">TP ' + pgTxt(g) + '</span>' : '') +
                               (l !== null ? '<span style="color:' + C_SL + '">SL ' + pgTxt(l) + '</span>' : '');
        }
        ed._revisar = revisar;
        ed.addEventListener('input', revisar);
        ed.addEventListener('change', revisar);
        // que escribir aquí no active los atajos del gráfico (Supr borra dibujos, etc.)
        ed.addEventListener('keydown', function(e){
          e.stopPropagation();
          if (e.key === 'Escape') cerrarEditor();
          if (e.key === 'Enter' && !q('.ok').disabled) q('.ok').click();
        });
        ed.addEventListener('mousedown', function(e){ e.stopPropagation(); });
        q('.cx').onclick = cerrarEditor;
        q('.del').onclick = function(){
          q('.del').disabled = q('.ok').disabled = true;
          post('/orden/eliminar', {ticket: +it.tk}).then(function(res){
            if (res.error){ q('.msg').textContent = res.error; q('.del').disabled = false; revisar(); return; }
            delete ORD[it.tk]; unir(); cerrarEditor();
            avisar(TIPO[it.t] + ' #' + it.tk + ' eliminada', false);
          });
        };
        q('.ok').onclick = function(){
          var v = leer();
          q('.ok').disabled = q('.del').disabled = true; q('.ok').textContent = 'Enviando…';
          post('/orden/modificar', {ticket: +it.tk, precio: redondear(v.po), sl: redondear(v.sl), tp: redondear(v.tp),
                                    caducidad: v.tt, expiracion: v.tt === 'specified' ? aServidor(v.ex) : 0})
            .then(function(res){
              if (!ed) return;
              if (res.error){
                q('.msg').textContent = res.error; q('.ok').textContent = 'Modificar'; q('.del').disabled = false; revisar();
                return;
              }
              var src = ORD[it.tk];
              if (src){ src.po = res.price; src.sl = res.sl; src.tp = res.tp; src.tt = res.tt; src.ex = res.ex; }
              cerrarEditor();
              avisar(TIPO[it.t] + ' #' + it.tk + ' modificada', false);
            });
        };
        capa.appendChild(ed);
        revisar();
        q('.i-po').focus();
      }

