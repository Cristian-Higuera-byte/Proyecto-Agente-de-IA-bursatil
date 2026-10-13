// [grafico] Pantalla completa: botón, modo "pj-fs" y selector de activo (cambiar de símbolo sin salir)
    // Se pone en pantalla completa el IFRAME entero (window.frameElement), no solo el gráfico: así sigue en pantalla
    // completa aunque Streamlit recargue el contenido (p. ej. al cambiar de activo). Si no se puede, se usa el
    // contenedor del gráfico como antes. En pantalla completa se ven los botones VENDER/COMPRAR (posiciones_grafico.py)
    // y el nombre del activo abre la lista de activos de la watchlist.
    var ACTIVOS = __ACTIVOS_JSON__;
    var wrapFs = document.getElementById('tv-wrap');
    var btnFullEl = document.getElementById('btn-full');
    var docPadre = null;
    try { docPadre = window.parent.document; } catch (e) {}

    function enPantallaCompleta(){
      var fe = docPadre ? docPadre.fullscreenElement : document.fullscreenElement;
      if (!fe && document.fullscreenElement) fe = document.fullscreenElement;
      return !!fe && (fe === window.frameElement || fe === wrapFs);
    }
    function alternarPantallaCompleta(){
      if (enPantallaCompleta()) {
        var d = (docPadre && docPadre.fullscreenElement) ? docPadre : document;
        if (d.exitFullscreen) d.exitFullscreen();
        return;
      }
      var respaldo = function(){ if (wrapFs.requestFullscreen) wrapFs.requestFullscreen(); };
      var fe = window.frameElement;
      if (fe && fe.requestFullscreen) {
        var p = null;
        try { p = fe.requestFullscreen(); } catch (e) { respaldo(); return; }
        if (p && p.catch) p.catch(respaldo);
      } else { respaldo(); }
    }
    if (btnFullEl) btnFullEl.addEventListener('click', alternarPantallaCompleta);

    // --- Selector de activo ---
    var panelSel = document.getElementById('sel-activo');
    var listaSel = document.getElementById('sel-activo-lista');
    var msgSel = document.getElementById('sel-activo-msg');
    var simboloEl = document.getElementById('lg-sym');

    function construirSelector(){
      listaSel.innerHTML = '';
      ACTIVOS.forEach(function(a, i){
        var fila = document.createElement('div'); fila.className = 'sel-fila';
        var ico = document.createElement('div'); ico.className = 'sel-ico'; ico.innerHTML = a.i || '';
        var txt = document.createElement('div'); txt.className = 'sel-txt';
        var nom = document.createElement('span'); nom.className = 'sel-nom'; nom.textContent = a.b;
        txt.appendChild(nom);
        if (a.n) { var de = document.createElement('span'); de.className = 'sel-desc'; de.textContent = a.n; txt.appendChild(de); }
        fila.appendChild(ico); fila.appendChild(txt);
        if (a.a) { var ok = document.createElement('span'); ok.className = 'sel-ok'; ok.textContent = String.fromCharCode(10003); fila.appendChild(ok); }
        fila.addEventListener('click', function(){ elegirActivo(i); });
        listaSel.appendChild(fila);
      });
    }
    function abrirSelectorActivo(){
      if (!enPantallaCompleta() || !ACTIVOS.length) return;
      msgSel.textContent = '';
      construirSelector();
      panelSel.classList.add('abierto');
    }
    function cerrarSelectorActivo(){ panelSel.classList.remove('abierto'); }
    function elegirActivo(i){
      var a = ACTIVOS[i];
      if (!a) return;
      if (a.a) { cerrarSelectorActivo(); return; }
      // Streamlit tiene un botón oculto por activo (posiciones_grafico.gatillos_cierre): se pulsa el nº i
      var b = null;
      try { b = docPadre.querySelector('.st-key-chcls_sel_' + i + ' button'); } catch (e) {}
      if (!b) { msgSel.textContent = 'No se pudo cambiar de activo desde aquí. Sal de la pantalla completa y elígelo en la lista.'; return; }
      msgSel.textContent = 'Cambiando a ' + a.b + '…';
      b.click();
    }
    if (simboloEl) simboloEl.addEventListener('click', function(e){
      e.stopPropagation();
      if (panelSel.classList.contains('abierto')) cerrarSelectorActivo(); else abrirSelectorActivo();
    });
    document.getElementById('sel-activo-x').addEventListener('click', cerrarSelectorActivo);
    document.addEventListener('mousedown', function(e){
      if (panelSel.classList.contains('abierto') && !panelSel.contains(e.target) && e.target !== simboloEl) cerrarSelectorActivo();
    });
    document.addEventListener('keydown', function(e){ if (e.key === 'Escape') cerrarSelectorActivo(); });

    // --- Modo pantalla completa (clase pj-fs): se revisa a menudo porque el evento llega al documento padre ---
    var fsPrevio = null;
    function sincronizarPantalla(){
      var fs = enPantallaCompleta();
      if (fs === fsPrevio) return;
      fsPrevio = fs;
      wrapFs.classList.toggle('pj-fs', fs);
      if (!fs) cerrarSelectorActivo();
      redibujarTodo();
    }
    setInterval(sincronizarPantalla, 200);
    sincronizarPantalla();
