(function(){
  var P = window.parent, D, H;
  try { D = P.document; H = D.documentElement; } catch(e) { return; }
  function estado(){
    if (H.classList.contains('pj-panel-dom')) return 'dom';
    if (H.classList.contains('pj-panel-none')) return 'none';
    return 'order';   // sin clase = Operar abierto (default al entrar / F5)
  }
  function poner(s){
    H.classList.toggle('pj-panel-dom', s === 'dom');
    H.classList.toggle('pj-panel-none', s === 'none');
  }
  if (P.__pjRailFn) D.removeEventListener('click', P.__pjRailFn, true);
  P.__pjRailFn = function(e){
    if (!(e.target && e.target.closest)) return;
    var bo = e.target.closest('.st-key-rail_order button');
    var bd = e.target.closest('.st-key-rail_dom button');
    if (!bo && !bd) return;
    e.stopPropagation(); e.preventDefault();
    var c = estado();
    if (bo) poner(c === 'order' ? 'none' : 'order');
    else    poner(c === 'dom' ? 'none' : 'dom');
  };
  D.addEventListener('click', P.__pjRailFn, true);
})();
