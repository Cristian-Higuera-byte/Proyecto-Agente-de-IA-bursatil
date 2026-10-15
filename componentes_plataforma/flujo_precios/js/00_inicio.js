(function(){
  var API = __API__;
  var P = window.parent, D;
  try { D = P.document; } catch(e) { return; }   // sin acceso al DOM padre: no hay feed

  var bc = ('BroadcastChannel' in window) ? new BroadcastChannel('pj-ticks') : null;
  var es = null, actuales = '', ultimo = {}, cuenta = null, pendiente = false;
  var spark = {}, sparkT = {}, sembrado = {};
  // Un punto nuevo por cada tick (el motor lee cada 250 ms y solo envía si el
  // precio cambió). 120 puntos ≈ 30 s de ticks en un símbolo muy activo.
  var SPARK_MAX = 120, SPARK_PASO = 250;

