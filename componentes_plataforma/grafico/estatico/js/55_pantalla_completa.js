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
   ----------------------------- INICIO Piña y Jara 55_pantalla_completa .JS -----------------------------
   ------------------------------------------------------------------------------------------------------- */

// [grafico] Pantalla completa: botón, modo "pj-fs" y selector de activo (cambiar de símbolo sin salir)
    // Se pone en pantalla completa el IFRAME entero (window.frameElement), no solo el gráfico: así sigue en pantalla
    // completa aunque Streamlit recargue el contenido (p. ej. al cambiar de activo). Si no se puede, se usa el
    // contenedor del gráfico como antes. En pantalla completa se ven los botones VENDER/COMPRAR (posiciones/)
    // y el nombre del activo abre la lista de activos de la watchlist.
    // ACTIVOS: lista de activos de la watchlist inyectada por Python (símbolo b, nombre n, icono i y marca a de activo actual)
    var ACTIVOS = __ACTIVOS_JSON__;
    // wrapFs / btnFullEl: contenedor del gráfico y botón de pantalla completa; docPadre: documento de Streamlit si es accesible
    var contenedorFs = document.getElementById('tradingview-contenedor');
    var botonCompletoEl = document.getElementById('boton-completo');
    var docPadre = null;
    try { docPadre = window.parent.document; } catch (e) {}

    // TITULO EN PANTALLA COMPLETA

    /**
     * Indica si la pantalla completa está activa sobre este iframe o sobre el contenedor del gráfico, consultando
     * también el documento padre de Streamlit.
     */
    function enPantallaCompleta(){
      var fe = docPadre ? docPadre.fullscreenElement : document.fullscreenElement;
      if (!fe && document.fullscreenElement) fe = document.fullscreenElement;
      return !!fe && (fe === window.frameElement || fe === contenedorFs);
    }
    // TITULO ALTERNAR PANTALLA COMPLETA

    /**
     * Entra o sale de pantalla completa: pide pantalla completa del iframe entero (o del contenedor si no es posible)
     * y sale usando el documento que la tiene.
     */
    function alternarPantallaCompleta(){
      if (enPantallaCompleta()) {
        var d = (docPadre && docPadre.fullscreenElement) ? docPadre : document;
        if (d.exitFullscreen) d.exitFullscreen();
        return;
      }
      /** Alternativa de alternarPantallaCompleta: pone en pantalla completa solo el contenedor del gráfico. */
      var respaldo = function(){ if (contenedorFs.requestFullscreen) contenedorFs.requestFullscreen(); };
      var fe = window.frameElement;
      if (fe && fe.requestFullscreen) {
        var p = null;
        try { p = fe.requestFullscreen(); } catch (e) { respaldo(); return; }
        if (p && p.catch) p.catch(respaldo);
      } else { respaldo(); }
    }
    if (botonCompletoEl) botonCompletoEl.addEventListener('click', alternarPantallaCompleta);

    // --- Selector de activo ---
    // Elementos del selector de activo
    var panelSeleccion = document.getElementById('seleccion-activo');
    var listaSeleccion = document.getElementById('seleccion-activo-lista');
    var mensajeSeleccion = document.getElementById('seleccion-activo-mensaje');
    var simboloEl = document.getElementById('leyenda-simbolo');

    // TITULO CONSTRUIR SELECTOR

    /**
     * Dibuja la lista de activos de la watchlist (icono, nombre, descripción y marca del activo actual) y asocia el
     * clic a elegirActivo.
     */
    function construirSelector(){
      listaSeleccion.innerHTML = '';
      ACTIVOS.forEach(function(a, i){
        var fila = document.createElement('div'); fila.className = 'seleccion-fila';
        var ico = document.createElement('div'); ico.className = 'seleccion-icono'; ico.innerHTML = a.i || '';
        var txt = document.createElement('div'); txt.className = 'seleccion-texto';
        var nom = document.createElement('span'); nom.className = 'seleccion-nombre'; nom.textContent = a.b;
        txt.appendChild(nom);
        if (a.n) { var de = document.createElement('span'); de.className = 'seleccion-descripcion'; de.textContent = a.n; txt.appendChild(de); }
        fila.appendChild(ico); fila.appendChild(txt);
        if (a.a) { var ok = document.createElement('span'); ok.className = 'seleccion-aceptar'; ok.textContent = String.fromCharCode(10003); fila.appendChild(ok); }
        fila.addEventListener('click', function(){ elegirActivo(i); });
        listaSeleccion.appendChild(fila);
      });
    }
    // TITULO ABRIR SELECTOR ACTIVO

    /** Muestra el panel selector de activo; solo funciona en pantalla completa y si hay activos. */
    function abrirSelectorActivo(){
      if (!enPantallaCompleta() || !ACTIVOS.length) return;
      mensajeSeleccion.textContent = '';
      construirSelector();
      panelSeleccion.classList.add('abierto');
    }
    // TITULO CERRAR SELECTOR ACTIVO

    /** Oculta el panel selector de activo. */
    function cerrarSelectorActivo(){ panelSeleccion.classList.remove('abierto'); }
    // TITULO ELEGIR ACTIVO

    /**
     * Cambia al activo número i pulsando el botón oculto de Streamlit correspondiente; si no se puede, muestra un
     * mensaje.
     */
    function elegirActivo(i){
      var a = ACTIVOS[i];
      if (!a) return;
      if (a.a) { cerrarSelectorActivo(); return; }
      // Streamlit tiene un botón oculto por activo (posiciones_grafico.gatillos_cierre): se pulsa el nº i
      var b = null;
      try { b = docPadre.querySelector('.st-key-grafico_cerrar_sel_' + i + ' button'); } catch (e) {}
      if (!b) { mensajeSeleccion.textContent = 'No se pudo cambiar de activo desde aquí. Sal de la pantalla completa y elígelo en la lista.'; return; }
      mensajeSeleccion.textContent = 'Cambiando a ' + a.b + '…';
      b.click();
    }
    // Eventos del selector: el nombre del activo lo abre o cierra; la X, un clic fuera o Escape lo cierran
    if (simboloEl) simboloEl.addEventListener('click', function(e){
      e.stopPropagation();
      if (panelSeleccion.classList.contains('abierto')) cerrarSelectorActivo(); else abrirSelectorActivo();
    });
    document.getElementById('seleccion-activo-x').addEventListener('click', cerrarSelectorActivo);
    document.addEventListener('mousedown', function(e){
      if (panelSeleccion.classList.contains('abierto') && !panelSeleccion.contains(e.target) && e.target !== simboloEl) cerrarSelectorActivo();
    });
    document.addEventListener('keydown', function(e){ if (e.key === 'Escape') cerrarSelectorActivo(); });

    // --- Modo pantalla completa (clase pj-fs): se revisa a menudo porque el evento llega al documento padre ---
    // fsPrevio: último estado de pantalla completa visto, para detectar cambios
    var fsPrevio = null;
    // TITULO SINCRONIZAR PANTALLA

    /**
     * Revisa si cambió el estado de pantalla completa: actualiza la clase pj-fs, cierra el selector al salir y
     * redibuja los dibujos.
     */
    function sincronizarPantalla(){
      var fs = enPantallaCompleta();
      if (fs === fsPrevio) return;
      fsPrevio = fs;
      contenedorFs.classList.toggle('pj-fs', fs);
      if (!fs) cerrarSelectorActivo();
      redibujarTodo();
    }
    // Se revisa cada 200 ms porque el evento de pantalla completa llega al documento padre
    setInterval(sincronizarPantalla, 200);
    sincronizarPantalla();

/* -------------------------------------------------------------------------------------------------------
   ------------------------------- FIN Piña y Jara 55_pantalla_completa .JS ------------------------------
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
