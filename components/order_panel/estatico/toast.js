// Aviso flotante (toast) del resultado de la orden, inyectado en el documento PADRE.
// toast.py reemplaza los marcadores __FONDO__ / __ICONO__ / __NONCE__ / __MSG__ y lo
// envuelve en <script>. El __NONCE__ evita que se repita en cada refresco del fragmento.
(function(){
  var P = window.parent, D; try { D = P.document; } catch(e) { return; }
  if (P.__pjToastNonce === __NONCE__) return;   // ya mostrado para este resultado
  P.__pjToastNonce = __NONCE__;
  var vj = D.getElementById('pj-toast'); if (vj) vj.remove();
  var el = D.createElement('div'); el.id = 'pj-toast';
  el.style.cssText = 'position:fixed;right:22px;bottom:56px;z-index:100010;max-width:380px;'+
    'display:flex;align-items:flex-start;gap:10px;padding:13px 14px;border-radius:12px;'+
    'background:__FONDO__;color:#fff;font:600 13.5px system-ui,sans-serif;'+
    'box-shadow:0 10px 30px rgba(0,0,0,.45);opacity:0;transform:translateY(8px);'+
    'transition:opacity .2s ease,transform .2s ease;';
  el.innerHTML = '<span style="font-size:18px;line-height:1.2">__ICONO__</span>'+
    '<span style="flex:1;line-height:1.4">'+__MSG__+'</span>'+
    '<span id="pj-tx" style="cursor:pointer;opacity:.85;font-size:15px;padding:0 2px">&#10005;</span>';
  D.body.appendChild(el);
  P.requestAnimationFrame(function(){ el.style.opacity='1'; el.style.transform='translateY(0)'; });
  var tmr;
  function cerrar(){
    if (!el) return;
    el.style.opacity='0'; el.style.transform='translateY(8px)';
    P.setTimeout(function(){ if (el && el.parentNode) el.parentNode.removeChild(el); }, 220);
    el = null; P.clearTimeout(tmr);
  }
  el.querySelector('#pj-tx').onclick = cerrar;
  tmr = P.setTimeout(cerrar, 6000);
})();
