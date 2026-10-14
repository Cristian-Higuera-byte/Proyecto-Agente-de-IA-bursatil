  function pintar(solo){
    D.querySelectorAll('[data-pj-s]').forEach(function(el){
      var s = el.getAttribute('data-pj-s');
      if (solo && !(s in solo)) return;
      var t = ultimo[s];
      if (t) pintarElem(el, t);
    });
    D.querySelectorAll('[data-pj-spark]').forEach(function(el){
      var s = el.getAttribute('data-pj-spark');
      if (!solo || (s in solo)) pintarSpark(el, s);
    });
    pintarCuenta();
  }

  function simbolos(){
    var set = {};
    D.querySelectorAll('[data-pj-s]').forEach(function(el){ set[el.getAttribute('data-pj-s')] = 1; });
    return Object.keys(set).sort().join(',');
  }

  function conectar(lista){
    if (es) es.close();
    actuales = lista;
    es = new EventSource(API + '/stream?s=' + encodeURIComponent(lista));
    es.onmessage = function(ev){
      var m;
      try { m = JSON.parse(ev.data); } catch(e) { return; }
      sembrarSparks();
      for (var k in m.t){ ultimo[k] = m.t[k]; empujarSpark(k, m.t[k].l); }
      if (m.acc) cuenta = m.acc;
      pintar(m.t);
      if (bc) bc.postMessage(m);
    };
  }

  // Revisa si cambió el conjunto de símbolos (cambio de vista/activo) y repinta
  // lo que Streamlit acaba de redibujar con valores viejos.
  function revisar(){
    pendiente = false;
    sembrarSparks();                   // la tarjeta redibujada puede traer semilla nueva
    var lista = simbolos();
    if (lista && lista !== actuales) conectar(lista);
    pintar(null);
  }
  // El callback del MutationObserver corre ANTES de que el navegador pinte el
  // cambio: repintar aquí mismo hace que nunca se vea el valor/mini-gráfico viejo
  // que trae el refresco de respaldo de Streamlit (antes se veía ~120 ms → parpadeo).
  // La reconexión por cambio de símbolos sí va con retardo (no es urgente).
  new MutationObserver(function(){
    sembrarSparks();
    pintar(null);
    if (pendiente) return;
    pendiente = true;
    setTimeout(revisar, 120);
  }).observe(D.body, {childList: true, subtree: true});

