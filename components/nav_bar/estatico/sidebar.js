// Expandir / colapsar la barra lateral SIN reejecutar Python (animado).
// Lo carga barra.py con components.html(..., height=0). El clic del ☰ (que vive en la
// barra superior, .st-key-top_toggle) se intercepta en fase de CAPTURA en el documento
// padre y se hace stopPropagation para que NO dispare un rerun de Streamlit; solo se
// alterna la clase pj-sb-exp en <html> y el CSS anima anchos y márgenes.
// Al cargar la página (o iniciar sesión) la barra parte SIEMPRE retraída.
(function(){
  var P = window.parent, D, H;
  try { D = P.document; H = D.documentElement; } catch(e) { return; }
  function aplicar(exp){ H.classList.toggle('pj-sb-exp', exp); }
  // La bandera vive en la ventana: si Streamlit recrea este iframe al navegar
  // entre vistas, NO se vuelve a cerrar; se mantiene como el usuario la dejó.
  if (!P.__pjSbIniciada){
    P.__pjSbIniciada = true;
    H.classList.add('pj-sb-sinanim');
    aplicar(false);
    P.setTimeout(function(){ H.classList.remove('pj-sb-sinanim'); }, 80);
  }

  // Un solo oyente en el documento padre (se reemplaza si el iframe se recrea).
  // Fase de CAPTURA en document: corre antes que React; stopPropagation evita
  // que el clic dispare un rerun de Streamlit.
  if (P.__pjSbFn) D.removeEventListener('click', P.__pjSbFn, true);
  P.__pjSbFn = function(e){
    var b = e.target && e.target.closest && e.target.closest('.st-key-top_toggle button');
    if (!b) return;
    e.stopPropagation(); e.preventDefault();
    aplicar(!H.classList.contains('pj-sb-exp'));
  };
  D.addEventListener('click', P.__pjSbFn, true);
})();
