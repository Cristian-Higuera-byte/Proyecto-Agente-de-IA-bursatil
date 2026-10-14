  function pintarElem(el, t){
    var f = el.getAttribute('data-pj-f') || 'px';
    var pre = el.getAttribute('data-pj-pre') || '';
    var v;
    if (f === 'var'){
      var d = dec(el, t.l);
      var up = el.getAttribute('data-pj-up') || '#3fb950';
      var dn = el.getAttribute('data-pj-dn') || '#f85149';
      poner(el, (t.ch >= 0 ? '+' : '') + fmt(t.ch, d) + ' (' + (t.pct >= 0 ? '+' : '') + t.pct.toFixed(2) + '%)');
      color(el, t.ch >= 0 ? up : dn);
      return;
    }
    if (f === 'ch' || f === 'pct'){
      // cambio del día por separado (tablas): 'ch' en precio, 'pct' en % con flecha;
      // data-pj-pill="1" también pinta el fondo (pastilla verde/roja)
      var sube = t.ch >= 0;
      var txt = (f === 'ch') ? (sube ? '+' : '') + fmt(t.ch, dec(el, t.l))
                             : (sube ? '▲ +' : '▼ ') + t.pct.toFixed(2) + '%';
      poner(el, txt);
      color(el, sube ? (el.getAttribute('data-pj-up') || '#3fb950')
                     : (el.getAttribute('data-pj-dn') || '#f85149'));
      if (el.getAttribute('data-pj-pill') === '1'){
        var bg = sube ? 'rgba(63,185,80,.12)' : 'rgba(248,81,73,.12)';
        if (el.style.background !== bg) el.style.background = bg;
      }
      return;
    }
    if (f === 'spr'){
      var pip = parseFloat(el.getAttribute('data-pj-pip')) || 0;
      if (!pip) return;
      var s = (t.a - t.b) / pip;
      poner(el, s < 100 ? fmt(s, 1) : fmt(s, 0));
      return;
    }
    if (f === 'bid') v = t.b;
    else if (f === 'ask') v = t.a;
    else if (f === 'side') v = (el.getAttribute('data-pj-side') === 'SELL') ? t.b : t.a;
    else v = t.l;
    if (!v) return;
    poner(el, pre + fmt(v, dec(el, v)));
    if (el.getAttribute('data-pj-flash') === '1'){
      var prev = parseFloat(el.getAttribute('data-pj-prev'));
      if (!isNaN(prev) && v !== prev) color(el, v > prev ? '#3fb950' : '#f85149');
      el.setAttribute('data-pj-prev', String(v));
    }
  }

