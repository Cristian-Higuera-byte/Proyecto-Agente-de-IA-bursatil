/*
Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
Dirección: José Joaquín Prieto #5373 -
San Miguel - Santiago - Chile
contacto.pinayjara@gmail.com
https://www.pinayjara.cl
Creado, Programado y Diseñado por Piña y Jara
Transportes y Servicios Ltda.
*/


/* -------------------------------------------------------------------------------------------------------
   ---------------------------------- INICIO Piña y Jara 99_en_vivo .JS ----------------------------------
   ------------------------------------------------------------------------------------------------------- */

      // En vivo: Bid/Ask (ticks, canal público) y altas/bajas/SL/TP/P-G (mensaje de cuenta del feed, canal PRIVADO de esta sesión y cuenta). V12 de la auditoría: antes todo iba por un canal
      // de nombre fijo que escuchaban todas las pestañas del navegador, así que otra cuenta recibía estas posiciones y podía publicar mensajes que las cambiaban. Ahora el nombre del canal privado
      // lleva un secreto de esta sesión (CANAL) y la cuenta, y además se descarta cualquier mensaje de cuenta que no sea de la cuenta de este gráfico.
      if ('BroadcastChannel' in window){
        var CANAL = __CANAL__;
        /** Cuenta a la que apunta la dirección del servidor de datos de este gráfico: «demo», «real» o «local». */
        function cuentaDe(url){ var m = /\/t\/(demo|real)\/?$/.exec(url || ''); return m ? m[1] : 'local'; }
        var CUENTA = cuentaDe(API);
        /** Tick del símbolo del gráfico (por nombre mostrado o por nombre real): actualiza BID/ASK y el desfase horario. */
        function alTick(d){
          var t = d.t && (d.t[SIMBOLO] || d.t[REAL]);
          if (t && t.b){
            BID = t.b; ASK = t.a;
            if (t.t) OFF = Math.round((t.t - Date.now() / 1000) / 900) * 900;
            if (ed && ed._revisar && document.activeElement && !ed.contains(document.activeElement)) ed._revisar();
          }
        }
        /**
         * Mensaje de cuenta del feed: d.acc trae el estado de la cuenta y d.cuenta de qué cuenta es. Se ignora si no es de la cuenta de este gráfico.
         * Reconstruye POS y ORD cuando cambian (acc.pi posiciones, acc.ord órdenes, acc.pos P/G, acc.pc precio actual).
         */
        function alCuenta(d){
          var acc = d.acc;
          if (!acc || d.cuenta !== CUENTA) return;
          if (acc.pi){
            // Lista completa de posiciones: se reconstruye solo con las del símbolo y se les adjunta P/G (p) y precio actual (pc).
            var np = {};
            for (var tk in acc.pi){
              var x = acc.pi[tk];
              if (x.s !== REAL) continue;
              np[tk] = {s: x.s, t: x.t, v: x.v, po: x.po, sl: x.sl, tp: x.tp, k: x.k, sm: x.sm,
                        tr: x.tr, p: (acc.pos || {})[tk], pc: (acc.pc || {})[tk]};
            }
            POSICION = np;
          } else {
            // Sin lista nueva: solo se actualizan P/G y precio actual de las posiciones existentes.
            for (var tk2 in POSICION){
              if (acc.pos && tk2 in acc.pos) POSICION[tk2].p = acc.pos[tk2];
              if (acc.pc && tk2 in acc.pc) POSICION[tk2].pc = acc.pc[tk2];
            }
          }
          if (acc.ord){
            // Lista completa de órdenes pendientes del símbolo.
            var no = {};
            for (var tk3 in acc.ord){ var o = acc.ord[tk3]; if (o.s === REAL) no[tk3] = o; }
            ORDEN = no;
          }
          // Si cambió alguna lista se recrean o borran las líneas.
          if (acc.pi || acc.ord) unir();
        }
        new BroadcastChannel('pj-ticks').addEventListener('message', function(ev){ alTick(ev.data || {}); });
        new BroadcastChannel('pj-cuenta-' + CANAL + '-' + CUENTA).addEventListener('message', function(ev){ alCuenta(ev.data || {}); });
      }
      // ¿El servidor de datos en ejecución es la versión que espera este código?
      // Versión mínima de la API del servidor que espera este código.
      var V_API = 6;
      fetch(API + '/salud', {credentials: 'include'}).then(function(r){ return r.json(); }).then(function(r){
        if (!r.v || r.v < V_API){
          avisar('El servidor de datos está desactualizado: reinicia servidor_datos.py', true);
          var el = document.getElementById('pj-posicion-aviso'); clearTimeout(tAviso);
          if (el) el.style.whiteSpace = 'normal';
        }
      }).catch(function(){});
      unir();
      // Arranque: primer armado de líneas con los datos iniciales y comienzo del bucle de dibujo.
      // Aquí termina la función autoejecutable abierta en 00_inicio.js.
      ubicar();
    })();

/* -------------------------------------------------------------------------------------------------------
   ------------------------------------ FIN Piña y Jara 99_en_vivo .JS -----------------------------------
   ------------------------------------------------------------------------------------------------------- */

/*
Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
Dirección: José Joaquín Prieto #5373 -
San Miguel - Santiago - Chile
contacto.pinayjara@gmail.com
https://www.pinayjara.cl
Creado, Programado y Diseñado por Piña y Jara
Transportes y Servicios Ltda.
*/
