// [grafico] Tiempo real, temporalidades, captura y pantalla completa
    // --- Ticks en vivo del feed SSE (components/live_feed.py) ---------------
    // El feed reenvía cada tick por BroadcastChannel('pj-ticks'); aquí se mueve
    // la vela actual (o se abre una nueva al cambiar de periodo) al instante.
    var TF_SEG = {M1: 60, M5: 300, M15: 900, M30: 1800, H1: 3600, H4: 14400, D1: 86400};
    var ultimoTickBC = 0, ultimoPoll = 0, rafTick = false;
    if ('BroadcastChannel' in window){
      var bcTicks = new BroadcastChannel('pj-ticks');
      bcTicks.onmessage = function(ev){
        var t = ev.data && ev.data.t && ev.data.t[SIMBOLO];
        if (!t || !t.b || cargando || !datosActuales.length) return;
        ultimoTickBC = Date.now();
        var px = t.b;                       // las velas de MT5 se construyen con el Bid
        var ultima = datosActuales[datosActuales.length - 1];
        var seg = TF_SEG[tfActual];
        var inicio = seg ? Math.floor(t.t / seg) * seg : ultima.time;
        if (inicio > ultima.time){
          datosActuales.push({time: inicio, open: px, high: px, low: px, close: px, volume: 0});
        } else if (inicio === ultima.time){
          datosActuales[datosActuales.length - 1] = Object.assign({}, ultima, {
            close: px, high: Math.max(ultima.high, px), low: Math.min(ultima.low, px)
          });
        } else {
          return;
        }
        if (rafTick) return;                // como máximo un repintado por frame
        rafTick = true;
        requestAnimationFrame(function(){
          rafTick = false;
          var v = datosActuales[datosActuales.length - 1];
          var f = formatearDatos(datosActuales, tipoActual);
          serie.update(f[f.length - 1]);
          serieVolumen.update(aPuntoVolumen(v));
          actualizarLeyenda(v);
          actualizarIndicadoresTick();
          redibujarTodo();
        });
      };
    }

    setInterval(function(){
      if (cargando || pollEnCurso || !datosActuales.length) return;
      // Con el feed entregando ticks, el polling solo resincroniza (volumen real,
      // vela cerrada) cada 5 s en vez de cada 1,5 s.
      if (Date.now() - ultimoTickBC < 4000 && Date.now() - ultimoPoll < 5000) return;
      ultimoPoll = Date.now();
      var tfLlamada = tfActual;
      var idLlamada = cargaId;
      pollEnCurso = true;
      fetch(API + "/ultima/" + encodeURIComponent(SIMBOLO) + "?tf=" + tfLlamada)
        .then(function(r){ return r.json(); })
        .then(function(v){
          if (tfLlamada !== tfActual || idLlamada !== cargaId) return;
          if (v && v.time){
            var ultima = datosActuales[datosActuales.length - 1];
            if (v.time < ultima.time) return;
            if (ultima.time === v.time){
              datosActuales[datosActuales.length - 1] = v;
            } else {
              datosActuales.push(v);
            }
            var datosFormateados = formatearDatos(datosActuales, tipoActual);
            serie.update(datosFormateados[datosFormateados.length - 1]);
            serieVolumen.update(aPuntoVolumen(v));
            actualizarLeyenda(v);
            actualizarIndicadoresTick();
            redibujarTodo();
          }
        })
        .catch(function(){})
        .then(function(){ pollEnCurso = false; });
    }, 1500);

    chart.subscribeCrosshairMove(function(param){
      if (!param || !param.time){
        if (datosActuales.length) actualizarLeyenda(datosActuales[datosActuales.length - 1]);
        return;
      }
      var idx = datosActuales.findIndex(function(d){ return d.time === param.time; });
      if (idx >= 0) actualizarLeyenda(datosActuales[idx]);
    });

    function marcarTF(tf){
      document.querySelectorAll('.tvtf').forEach(function(b){
        b.classList.toggle('active', b.getAttribute('data-tf') === tf);
      });
    }

    document.querySelectorAll('.tvtf').forEach(function(btn){
      btn.addEventListener('click', function(){
        var tf = btn.getAttribute('data-tf');
        marcarTF(tf);
        document.querySelectorAll('.tvrange').forEach(function(b){ b.classList.remove('active'); });
        cargar(tf, parseInt(btn.getAttribute('data-n'), 10), 'ultimas');
        guardarConfig();
      });
    });

    document.querySelectorAll('.tvrange').forEach(function(btn){
      btn.addEventListener('click', function(){
        var tf = btn.getAttribute('data-tf');
        document.querySelectorAll('.tvrange').forEach(function(b){ b.classList.remove('active'); });
        btn.classList.add('active');
        marcarTF(tf);
        cargar(tf, parseInt(btn.getAttribute('data-n'), 10), true);
        guardarConfig();
      });
    });

    var btnShot = document.getElementById('btn-shot');
    if (btnShot){
      btnShot.addEventListener('click', function(){
        try {
          var shot = chart.takeScreenshot();
          var selPrev = seleccionadoId, hovPrev = hoverId;
          seleccionadoId = null; hoverId = null;
          pintar();
          var out = document.createElement('canvas');
          out.width = shot.width; out.height = shot.height;
          var oc = out.getContext('2d');
          oc.drawImage(shot, 0, 0);
          oc.drawImage(canvas, 0, 0, shot.width, shot.height);
          seleccionadoId = selPrev; hoverId = hovPrev;
          redibujarTodo();

          var esc = shot.width / Math.max(1, cssW);
          var ahora = new Date();
          function dos(n){ return (n < 10 ? '0' : '') + n; }
          var fecha = ahora.getFullYear() + '-' + dos(ahora.getMonth() + 1) + '-' + dos(ahora.getDate()) + ' ' + dos(ahora.getHours()) + ':' + dos(ahora.getMinutes());
          oc.save();
          oc.textBaseline = 'top';
          oc.font = 'bold ' + Math.round(15 * esc) + 'px sans-serif';
          oc.fillStyle = '#ffffff';
          oc.fillText(SIMBOLO + '  ·  ' + tfActual, 14 * esc, 10 * esc);
          oc.font = Math.round(11 * esc) + 'px sans-serif';
          oc.fillStyle = '#8b949e';
          oc.textAlign = 'right';
          oc.fillText('P&J  ·  ' + fecha, shot.width - 74 * esc, 12 * esc);
          oc.restore();

          out.toBlob(function(blob){
            if (!blob) return;
            var url = URL.createObjectURL(blob);
            var enlace = document.createElement('a');
            enlace.download = SIMBOLO + '_' + tfActual + '_' + fecha.replace(/[- :]/g, '') + '.png';
            enlace.href = url;
            document.body.appendChild(enlace);
            enlace.click();
            document.body.removeChild(enlace);
            setTimeout(function(){ URL.revokeObjectURL(url); }, 2000);
          }, 'image/png');
        } catch (e) {}
      });
    }

    // (el botón de pantalla completa vive ahora en js/55_pantalla_completa.js)
