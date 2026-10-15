(function(){
  var P = window.parent, D;
  try { D = P.document; } catch(e) { return; }
  if (!D.getElementById('pj-mkt-load-css')){
    var st = D.createElement('style'); st.id = 'pj-mkt-load-css';
    st.textContent =
      '#pj-mkt-load{position:fixed;inset:0;z-index:999999;display:flex;align-items:center;justify-content:center;' +
      'background:rgba(5,8,14,.55);backdrop-filter:blur(3px);opacity:0;transition:opacity .18s ease;pointer-events:none;}' +
      '#pj-mkt-load.on{opacity:1;}' +
      '#pj-mkt-load .box{display:flex;flex-direction:column;align-items:center;gap:14px;background:#0d1117;' +
      'border:1px solid #30363d;border-radius:16px;padding:26px 34px;box-shadow:0 18px 50px rgba(0,0,0,.55);}' +
      '#pj-mkt-load .ring{width:46px;height:46px;border-radius:50%;' +
      'background:conic-gradient(from 0deg,rgba(255,75,75,0),#ff4b4b 55%,#ff8f00);' +
      '-webkit-mask:radial-gradient(farthest-side,transparent calc(100% - 5px),#000 calc(100% - 4px));' +
      'mask:radial-gradient(farthest-side,transparent calc(100% - 5px),#000 calc(100% - 4px));' +
      'animation:pjgira .8s linear infinite;}' +
      '#pj-mkt-load .t{color:#e6edf3;font:600 14px "Source Sans Pro",system-ui,sans-serif;}' +
      '#pj-mkt-load .s{color:#8b949e;font:12px "Source Sans Pro",system-ui,sans-serif;margin-top:-8px;}' +
      '@keyframes pjgira{to{transform:rotate(360deg);}}';
    D.head.appendChild(st);
  }
  var tope = null, obs = null;
  function ocultar(){
    var el = D.getElementById('pj-mkt-load');
    if (obs){ obs.disconnect(); obs = null; }
    if (tope){ clearTimeout(tope); tope = null; }
    if (!el) return;
    el.classList.remove('on');
    setTimeout(function(){ if (el.parentNode) el.parentNode.removeChild(el); }, 200);
  }
  function mostrar(nombre){
    ocultar();
    var el = D.createElement('div'); el.id = 'pj-mkt-load';
    el.innerHTML = '<div class="box"><div class="ring"></div><div class="t"></div>' +
                   '<div class="s">Cargando precios, gráfico y estadísticas</div></div>';
    el.querySelector('.t').textContent = nombre ? 'Abriendo ' + nombre + '…' : 'Abriendo ficha…';
    D.body.appendChild(el);
    requestAnimationFrame(function(){ el.classList.add('on'); });
    obs = new MutationObserver(function(){ if (D.querySelector('.st-key-fic_root')) ocultar(); });
    obs.observe(D.body, {childList: true, subtree: true});
    tope = setTimeout(ocultar, 20000);            // respaldo: nunca queda pegado
  }
  if (P.__pjMktLoadFn) D.removeEventListener('click', P.__pjMktLoadFn, true);
  P.__pjMktLoadFn = function(e){
    var b = e.target.closest && e.target.closest('[class*="st-key-mktclk_"] button');
    if (!b) return;
    var cont = b.closest('[class*="st-key-mktrow_"], [class*="st-key-mktcard_"]');
    var nm = cont && cont.querySelector('.mkt-nm b, .mkt-card-nm');
    mostrar(nm ? nm.textContent.trim() : '');
  };
  D.addEventListener('click', P.__pjMktLoadFn, true);   // captura: sin frenar el clic
})();
