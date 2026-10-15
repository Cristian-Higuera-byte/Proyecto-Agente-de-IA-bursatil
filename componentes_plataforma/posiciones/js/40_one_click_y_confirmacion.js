      // ---------- One-Click Trading: estado del interruptor del ticket ----------
      function ocInput(){ try { return PD.querySelector('.st-key-ord_oc input[type="checkbox"]'); } catch(e){ return null; } }
      function oneClick(){ var i = ocInput(); return !!(i && i.checked); }
      function alternarOneClick(){
        var i = ocInput();
        if (i) i.click();   // mismo interruptor del ticket: la 1.ª vez pide aceptar los términos
        else avisar('Abre el ticket de órdenes para cambiar One-Click Trading', true);
      }

      // Ejecuta `fn` al instante (One-Click) o tras confirmar en el gráfico
      function accion(titulo, desc, fn, alCancelar){
        cerrarConf(true);
        if (oneClick()){ fn(); return; }
        conf = document.createElement('div'); conf.id = 'pj-conf';
        conf.innerHTML = '<div class="t"></div><div class="d"></div><div class="bs">' +
          '<button class="no">Cancelar</button><button class="ok">Confirmar</button></div>' +
          '<div class="h"><a class="oc">Activar One-Click Trading</a> para operar sin confirmar.</div>';
        conf.querySelector('.t').textContent = titulo;
        conf.querySelector('.d').innerHTML = desc;
        conf._cancelar = alCancelar;
        conf.addEventListener('mousedown', function(e){ e.stopPropagation(); });
        conf.querySelector('.no').onclick = function(){ cerrarConf(true); };
        conf.querySelector('.ok').onclick = function(){ cerrarConf(false); fn(); };
        conf.querySelector('.oc').onclick = function(){ cerrarConf(true); alternarOneClick(); };
        capa.appendChild(conf);
      }
      function cerrarConf(cancelar){
        if (!conf) return;
        if (cancelar && conf._cancelar) conf._cancelar();
        if (conf.parentNode) conf.parentNode.removeChild(conf);
        conf = null;
      }

