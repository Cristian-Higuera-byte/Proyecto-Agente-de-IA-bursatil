      function fmt(v, d){ return Number(v).toLocaleString('en-US', {minimumFractionDigits: d, maximumFractionDigits: d}); }
      function txt(el, t){ if (el.textContent !== t) el.textContent = t; }
      function redondear(px){ var f = Math.pow(10, DIGITS); return Math.round(px * f) / f; }
      function esCompra(it){ return it.t === 0 || it.t === 2 || it.t === 4; }
      function precioEntrada(it, n){ return (n && n.pend.po !== undefined) ? n.pend.po : it.po; }
      // P/G si el precio llega a `px` (k = valor de 1 unidad de precio por lote)
      function pgEn(it, entrada, px){ return (esCompra(it) ? 1 : -1) * (px - entrada) * (it.k || K) * it.v; }
      function etiqueta(it){ return TIPO[it.t] + ' ' + fmt(it.v, 2); }

      // '' si es válido; si no, el motivo
      function validar(it, f, px, entrada){
        var m = it.sm || SM;
        if (f === 'po'){
          if (!BID || !ASK) return '';
          if (it.t === 2 && !(px < ASK - m)) return 'un Buy Limit debe quedar bajo el precio actual (Ask)';
          if (it.t === 4 && !(px > ASK + m)) return 'un Buy Stop debe quedar sobre el precio actual (Ask)';
          if (it.t === 3 && !(px > BID + m)) return 'un Sell Limit debe quedar sobre el precio actual (Bid)';
          if (it.t === 5 && !(px < BID - m)) return 'un Sell Stop debe quedar bajo el precio actual (Bid)';
          return '';
        }
        // posición: contra el precio actual; orden pendiente: contra su precio de entrada
        var ref = it.kind === 'ord' ? entrada : (it.pc || it.po), c = esCompra(it);
        var donde = it.kind === 'ord' ? 'el precio de entrada' : 'el precio actual';
        if (f === 'sl' && c && !(px < ref - m)) return 'en una compra el Stop Loss debe quedar bajo ' + donde;
        if (f === 'sl' && !c && !(px > ref + m)) return 'en una venta el Stop Loss debe quedar sobre ' + donde;
        if (f === 'tp' && c && !(px > ref + m)) return 'en una compra el Take Profit debe quedar sobre ' + donde;
        if (f === 'tp' && !c && !(px < ref - m)) return 'en una venta el Take Profit debe quedar bajo ' + donde;
        return '';
      }

      function avisar(t, malo){
        var el = document.getElementById('pj-pos-aviso');
        if (!el){ el = document.createElement('div'); el.id = 'pj-pos-aviso'; capa.appendChild(el); }
        el.textContent = t;
        el.style.borderColor = malo ? '#da3633' : '#2ea043';
        el.style.opacity = '1';
        clearTimeout(tAviso);
        tAviso = setTimeout(function(){ el.style.opacity = '0'; }, 3800);
      }

