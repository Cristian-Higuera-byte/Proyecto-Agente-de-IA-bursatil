// [grafico] Indicadores: ventana de selección
    // Renderizar lista en el modal de indicadores
    function renderizarListaIndicadores(filtro){
      var container = document.getElementById('ind-list-container');
      container.innerHTML = '';
      var textoFiltro = (filtro || '').toLowerCase();

      CATALOGO_INDICADORES.forEach(function(ind){
        if (textoFiltro && ind.nombre.toLowerCase().indexOf(textoFiltro) === -1 && ind.tipo.toLowerCase().indexOf(textoFiltro) === -1) return;
        
        var activo = indicadores[ind.id];
        var div = document.createElement('div');
        div.style.cssText = 'display:flex; align-items:center; justify-content:space-between; padding:10px 20px; cursor:pointer; transition:background 0.1s;';
        div.onmouseover = function(){ div.style.background = 'rgba(139,92,246,0.15)'; };
        div.onmouseout = function(){ div.style.background = 'transparent'; };

        div.innerHTML = '<div style="display:flex; flex-direction:column; gap:2px;">' +
                        '<span style="font-size:13px; color:#d1d4dc; font-weight:500;">' + ind.nombre + '</span>' +
                        '<span style="font-size:11px; color:#8b949e;">' + ind.tipo + '</span>' +
                        '</div>' +
                        '<span style="font-size:12px; font-weight:bold; padding:3px 8px; border-radius:4px; ' + 
                        (activo ? 'background:rgba(63,185,80,0.2); color:#3fb950;' : 'background:rgba(255,255,255,0.06); color:#8b949e;') + '">' + 
                        (activo ? 'Activo' : 'Añadir') + '</span>';

        div.addEventListener('click', function(){
          indicadores[ind.id] = !indicadores[ind.id];
          actualizarIndicadoresActivos();
          guardarConfig();
          renderizarListaIndicadores(document.getElementById('ind-search-input').value);
        });

        container.appendChild(div);
      });
    }

    var modalOverlay = document.getElementById('ind-modal-overlay');
    var btnIndSelect = document.getElementById('btn-ind-select');
    var modalClose = document.getElementById('ind-modal-close');
    var searchInput = document.getElementById('ind-search-input');

    btnIndSelect.addEventListener('click', function(e){
      e.stopPropagation();
      modalOverlay.style.display = 'flex';
      renderizarListaIndicadores('');
      setTimeout(function(){ searchInput.focus(); }, 50);
    });

    modalClose.addEventListener('click', function(){
      modalOverlay.style.display = 'none';
    });

    modalOverlay.addEventListener('click', function(e){
      if (e.target === modalOverlay) modalOverlay.style.display = 'none';
    });

    searchInput.addEventListener('input', function(e){
      renderizarListaIndicadores(e.target.value);
    });

