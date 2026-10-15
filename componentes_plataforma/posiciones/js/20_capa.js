      var capa = document.createElement('div'); capa.id = 'pj-pos';
      containerEl.parentNode.appendChild(capa);
      var ITEMS = {}, nodos = {}, drag = null, tAviso = null, menu = null, conf = null;
      // Etiqueta del precio en vivo (la nativa del gráfico se apagó en central_panel):
      // la dibujamos nosotros para que mida igual que las demás, llegue al borde y mande en el apilado.
      var liveEl = document.createElement('div'); liveEl.className = 'ej ejlive';
      liveEl.style.display = 'none'; capa.appendChild(liveEl);

