      function post(ruta, cuerpo){
        // text/plain = petición "simple" (sin preflight CORS)
        return fetch(API + ruta, {method: 'POST', headers: {'Content-Type': 'text/plain'}, body: JSON.stringify(cuerpo)})
          .then(function(r){ return r.json(); })
          .catch(function(){ return {error: 'Sin conexión con el servidor de datos'}; });
      }

      // Cambia SL / TP / precio de entrada de una posición u orden (px 0 = quitar SL/TP)
      function cambiarNivel(id, f, px){
        var it = ITEMS[id], n = nodos[id];
        if (!it || !n) return;
        n.pend[f] = px;
        var titulo = f === 'po' ? 'Mover ' + TIPO[it.t] : (px ? NOMBRE[f] : 'Quitar ' + NOMBRE[f]);
        var desc = '<b>' + etiqueta(it) + '</b> ' + REAL + (it.kind === 'ord' ? ' @ ' + fmt(it.po, DIGITS) : '') + '<br>' +
          (f === 'po' ? 'Nuevo precio de entrada: <b>' + fmt(px, DIGITS) + '</b>'
                      : (px ? NOMBRE[f] + ' en <b>' + fmt(px, DIGITS) + '</b>' : 'Se quitará el ' + NOMBRE[f]));
        accion(titulo, desc, function(){
          var cuerpo = {ticket: +it.tk};
          cuerpo[f === 'po' ? 'precio' : f] = px;
          post(it.kind === 'pos' ? '/sltp' : '/orden/modificar', cuerpo).then(function(res){
            delete n.pend[f];
            if (res.error){ avisar(res.error, true); return; }
            var src = it.kind === 'pos' ? POS[it.tk] : ORD[it.tk];
            if (src){ src.sl = res.sl; src.tp = res.tp; if (res.price) src.po = res.price; }
            avisar(f === 'po' ? TIPO[it.t] + ' movido a ' + fmt(px, DIGITS)
                              : (px ? NOMBRE[f] + ' en ' + fmt(px, DIGITS) : NOMBRE[f] + ' eliminado'), false);
          });
        }, function(){ delete n.pend[f]; });
      }

      function cancelarOrden(id){
        var it = ITEMS[id], n = nodos[id];
        if (!it || !n) return;
        n.pend.del = true;
        accion('Cancelar orden pendiente', '<b>' + etiqueta(it) + '</b> ' + REAL + ' @ ' + fmt(it.po, DIGITS), function(){
          post('/orden/eliminar', {ticket: +it.tk}).then(function(res){
            delete n.pend.del;
            if (res.error){ avisar(res.error, true); return; }
            delete ORD[it.tk]; unir();
            avisar(TIPO[it.t] + ' cancelada', false);
          });
        }, function(){ delete n.pend.del; });
      }

      function volumenTicket(){
        try {
          var i = PD.querySelector('.st-key-ord_vol input');
          var v = i ? parseFloat(String(i.value).replace(',', '.')) : NaN;
          return v > 0 ? v : VMIN;
        } catch(e){ return VMIN; }
      }

      function nuevaOrden(nombre, px){
        var vol = volumenTicket(), lado = nombre.indexOf('Buy') === 0 ? 'BUY' : 'SELL';
        accion('Nueva orden pendiente', '<b>' + nombre + ' ' + fmt(vol, 2) + '</b> ' + REAL +
               ' @ <b>' + fmt(px, DIGITS) + '</b><br>Good till cancelled (GTC)', function(){
          post('/orden', {symbol: REAL, lado: lado, volumen: vol, precio: px}).then(function(res){
            if (res.error){ avisar(res.error, true); return; }
            if (res.order){
              var t = {'Buy Limit': 2, 'Sell Limit': 3, 'Buy Stop': 4, 'Sell Stop': 5}[res.tipo] || (lado === 'BUY' ? 2 : 3);
              ORD[String(res.order)] = {s: REAL, t: t, v: res.volume, po: res.price, sl: 0, tp: 0, k: K, sm: SM};
              unir();
            }
            avisar((res.tipo || nombre) + ' ' + fmt(vol, 2) + ' colocada @ ' + fmt(res.price || px, DIGITS), false);
          });
        });
      }

