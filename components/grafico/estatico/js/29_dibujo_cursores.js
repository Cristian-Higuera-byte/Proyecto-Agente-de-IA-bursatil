// [grafico] Dibujo: tipos de cursor (cruce, punto, flecha, demostración) y borrador
    var modoCursor = 'cross';
    var demoPuntos = [];
    var CURSORES_PUROS = { dot: 1, pointer: 1, demo: 1 };

    function aplicarModoCursor(m){
      modoCursor = m;
      var linea = (m === 'cross');
      try {
        chart.applyOptions({ crosshair: { vertLine: { visible: linea, labelVisible: m === 'cross' || m === 'dot' }, horzLine: { visible: linea, labelVisible: m === 'cross' || m === 'dot' } } });
      } catch (e) {}
      wrapEl.classList.toggle('modo-punto', m === 'dot');
      wrapEl.classList.toggle('modo-flecha', m === 'pointer');
      wrapEl.classList.toggle('modo-demo', m === 'demo');
      if (m !== 'demo') { demoPuntos = []; redibujarTodo(); }
    }

    // El borrador es un modo de la herramienta de selección: con un clic sobre un dibujo lo elimina
    var modoBorrador = false;
    var activarAntesCursores = activarHerramienta;
    activarHerramienta = function(t){
      var borrador = (t === 'eraser');
      if (CURSORES_PUROS[t]) { aplicarModoCursor(t); t = 'cross'; }
      if (borrador) t = 'cross';
      modoBorrador = borrador;
      activarAntesCursores(t);
      var btn = document.getElementById('tool-cross');
      if (btn) { btn.setAttribute('data-tool', borrador ? 'eraser' : 'cross'); if (borrador) btn.classList.add('active'); }
      wrapEl.classList.toggle('modo-borrador', borrador);
      if (borrador) { seleccionadoId = null; redibujarTodo(); }
    };
    // elegir "Cruce" en el menú devuelve el cursor normal
    (function(){
      var it = document.querySelector('#cursor-flyout .tvtool-flyout-item[data-tool="cross"]');
      if (it) it.addEventListener('click', function(){ aplicarModoCursor('cross'); });
    })();

    window.addEventListener('mousedown', function(e){
      if (!modoBorrador || e.button !== 0 || bloqueado || !serie) return;
      if (!wrapEl.contains(e.target) || (e.target.closest && e.target.closest('.tv-ui'))) return;
      var pos = posMouse(e), ap = areaTrazado();
      if (pos.x < 0 || pos.y < 0 || pos.x > ap.w || pos.y > ap.h) return;
      var hit = elementoBajo(pos.x, pos.y);
      if (!hit) return;
      e.preventDefault(); e.stopPropagation();
      elementosDibujados.splice(hit.idx, 1); seleccionadoId = null; hoverId = null; confirmarCambio();
    }, true);
    window.addEventListener('mousemove', function(e){
      if (modoCursor === 'demo' && activeTool === 'cross' && !modoBorrador) {
        var p = posMouse(e);
        if (p.x >= 0 && p.y >= 0 && p.x <= cssW && p.y <= cssH) { demoPuntos.push({ x: p.x, y: p.y, t: Date.now() }); if (demoPuntos.length > 60) demoPuntos.shift(); redibujarTodo(); }
      }
    });
    wrapEl.addEventListener('mouseleave', function(){ if (demoPuntos.length) { demoPuntos = []; redibujarTodo(); } });

    // ---------- Demostración: puntero láser con estela ----------
    var pintarAntesCursores = pintar;
    pintar = function(){
      pintarAntesCursores();
      if (modoCursor !== 'demo' || !demoPuntos.length) return;
      var ahora = Date.now();
      demoPuntos = demoPuntos.filter(function(q){ return ahora - q.t < 650; });
      if (!demoPuntos.length) return;
      ctx.save();
      demoPuntos.forEach(function(q, i){
        var edad = (ahora - q.t) / 650;
        ctx.globalAlpha = Math.max(0, 0.5 * (1 - edad)); ctx.fillStyle = '#f23645';
        ctx.beginPath(); ctx.arc(q.x, q.y, 6 * (1 - edad * 0.5), 0, Math.PI * 2); ctx.fill();
      });
      var u = demoPuntos[demoPuntos.length - 1];
      var g = ctx.createRadialGradient(u.x, u.y, 0, u.x, u.y, 18);
      g.addColorStop(0, 'rgba(242,54,69,0.55)'); g.addColorStop(1, 'rgba(242,54,69,0)');
      ctx.globalAlpha = 1; ctx.fillStyle = g; ctx.beginPath(); ctx.arc(u.x, u.y, 18, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#f23645'; ctx.beginPath(); ctx.arc(u.x, u.y, 6, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 1.5; ctx.stroke();
      ctx.restore();
    };
    (function bucleDemo(){
      if (modoCursor === 'demo' && demoPuntos.length) redibujarTodo();   // la estela se apaga sola
      requestAnimationFrame(bucleDemo);
    })();
