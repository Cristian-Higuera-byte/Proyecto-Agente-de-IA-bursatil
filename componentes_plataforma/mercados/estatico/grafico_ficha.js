(function(){
  var D = __DATA__, DIG = __DIG__, SYM = __SYM__;
  var el = document.getElementById('chart');
  if (!window.LightweightCharts){ el.innerHTML = '<div style="color:#8b949e;font-size:12px;padding:20px;">No se pudo cargar el gráfico (sin internet).</div>'; return; }
  var ch = LightweightCharts.createChart(el, {
    autoSize: true,
    layout: { background: { type: 'solid', color: 'transparent' }, textColor: '#8b949e', fontSize: 11 },
    grid: { vertLines: { visible: false }, horzLines: { color: '#161d27' } },
    rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.12, bottom: 0.08 } },
    timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false },
    crosshair: { mode: 1, vertLine: { color: '#30363d', labelBackgroundColor: '#202a37' },
                 horzLine: { color: '#30363d', labelBackgroundColor: '#202a37' } },
    handleScroll: false, handleScale: false,
    localization: { priceFormatter: function(p){ return p.toLocaleString('en-US', {minimumFractionDigits: DIG, maximumFractionDigits: DIG}); } }
  });
  var serie = ch.addAreaSeries({ lineWidth: 2, priceLineVisible: false, lastValueVisible: true });
  var PER = [['1D','d'],['1S','w'],['1M',22],['3M',66],['6M',132],['1A',260]];
  var tabs = document.getElementById('tabs'), ley = document.getElementById('leyenda'), actual = null;
  var modo = 'd', horas = true;   // 'd' = 1 día (M5), 'w' = 1 semana (H1), número = días (D1)
  function fuente(){ return modo === 'd' ? D.m5 : (modo === 'w' ? D.h1 : D.d1); }
  function paso(){ return modo === 'd' ? 300 : (modo === 'w' ? 3600 : 86400); }
  var datos = [], sobre = false, raf = false;
  function fmt(v){ return v.toLocaleString('en-US', {minimumFractionDigits: DIG, maximumFractionDigits: DIG}); }
  function poner(k){
    modo = k; horas = (k === 'd' || k === 'w');
    datos = (typeof k === 'number' ? D.d1.slice(-k) : fuente()).slice();
    if (!datos.length) return;
    serie.setData(datos);
    colorear();
    ch.timeScale().fitContent();
  }
  function colorear(){
    var a = datos[0].value, b = datos[datos.length - 1].value, sube = b >= a;
    var c = sube ? '#3fb950' : '#f85149';
    serie.applyOptions({ lineColor: c, topColor: sube ? 'rgba(63,185,80,.28)' : 'rgba(248,81,73,.28)',
                         bottomColor: 'rgba(0,0,0,0)' });
    var p = (b / a - 1) * 100;
    actual = '<span style="color:' + c + ';font-weight:700;">' + (p >= 0 ? '+' : '') + p.toFixed(2) + '%</span> en el periodo' +
             ' &nbsp;<span style="color:#3fb950;">&#9679;</span> en vivo';
    if (!sobre) ley.innerHTML = actual;
  }
  // EN VIVO: el feed reenvía cada tick por BroadcastChannel('pj-ticks'); se mueve el
  // último punto (o se agrega uno al empezar otra hora / otro día). Bid, como MT5.
  function aplicarTick(t){
    if (!datos.length) return;
    var seg = paso(), ini = Math.floor(t.t / seg) * seg;
    var src = fuente(), ult = datos[datos.length - 1];
    var punto = {time: Math.max(ini, ult.time), value: t.b};
    if (punto.time > ult.time){ datos.push(punto); src.push(punto); }
    else { datos[datos.length - 1] = punto; src[src.length - 1] = punto; }
    if (raf) return; raf = true;
    requestAnimationFrame(function(){ raf = false; serie.update(datos[datos.length - 1]); colorear(); });
  }
  if ('BroadcastChannel' in window){
    new BroadcastChannel('pj-ticks').onmessage = function(ev){
      var t = ev.data && ev.data.t && ev.data.t[SYM];
      if (t && t.b && t.t) aplicarTick(t);
    };
  }
  PER.forEach(function(x, i){
    var b = document.createElement('button'); b.textContent = x[0];
    b.onclick = function(){ [].forEach.call(tabs.children, function(y){ y.className = ''; }); b.className = 'on'; poner(x[1]); };
    tabs.appendChild(b);
    if (x[0] === '1D'){ b.className = 'on'; }
  });
  poner(D.m5.length ? 'd' : 132);
  ch.subscribeCrosshairMove(function(pm){
    sobre = !!(pm && pm.time && pm.seriesData.get(serie));
    if (!sobre){ ley.innerHTML = actual; return; }
    var v = pm.seriesData.get(serie).value, f = new Date(pm.time * 1000);
    ley.innerHTML = '<span style="color:#e6edf3;font-weight:700;">' + fmt(v) + '</span> &nbsp;' +
      f.toLocaleDateString('es-CL', {day:'2-digit', month:'short', year:'numeric', timeZone:'UTC'}) +
      (horas ? ' ' + f.toISOString().substr(11, 5) : '');
  });
})();
