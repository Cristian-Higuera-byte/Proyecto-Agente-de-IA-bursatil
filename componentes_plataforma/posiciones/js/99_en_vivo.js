      // En vivo: Bid/Ask (ticks) y altas/bajas/SL/TP/P-G (mensaje de cuenta del feed)
      if ('BroadcastChannel' in window){
        new BroadcastChannel('pj-ticks').addEventListener('message', function(ev){
          var d = ev.data || {};
          var t = d.t && (d.t[SIMBOLO] || d.t[REAL]);
          if (t && t.b){
            BID = t.b; ASK = t.a;
            if (t.t) OFF = Math.round((t.t - Date.now() / 1000) / 900) * 900;
            if (ed && ed._revisar && document.activeElement && !ed.contains(document.activeElement)) ed._revisar();
          }
          var acc = d.acc;
          if (!acc) return;
          if (acc.pi){
            var np = {};
            for (var tk in acc.pi){
              var x = acc.pi[tk];
              if (x.s !== REAL) continue;
              np[tk] = {s: x.s, t: x.t, v: x.v, po: x.po, sl: x.sl, tp: x.tp, k: x.k, sm: x.sm,
                        tr: x.tr, p: (acc.pos || {})[tk], pc: (acc.pc || {})[tk]};
            }
            POS = np;
          } else {
            for (var tk2 in POS){
              if (acc.pos && tk2 in acc.pos) POS[tk2].p = acc.pos[tk2];
              if (acc.pc && tk2 in acc.pc) POS[tk2].pc = acc.pc[tk2];
            }
          }
          if (acc.ord){
            var no = {};
            for (var tk3 in acc.ord){ var o = acc.ord[tk3]; if (o.s === REAL) no[tk3] = o; }
            ORD = no;
          }
          if (acc.pi || acc.ord) unir();
        });
      }
      // ¿El servidor de datos en ejecución es la versión que espera este código?
      var V_API = 6;
      fetch(API + '/salud').then(function(r){ return r.json(); }).then(function(r){
        if (!r.v || r.v < V_API){
          avisar('El servidor de datos está desactualizado: reinicia servidor_datos.py', true);
          var el = document.getElementById('pj-pos-aviso'); clearTimeout(tAviso);
          if (el) el.style.whiteSpace = 'normal';
        }
      }).catch(function(){});
      unir();
      ubicar();
    })();
