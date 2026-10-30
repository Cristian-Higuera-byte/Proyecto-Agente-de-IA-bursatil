// Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
// Dirección: José Joaquín Prieto #5373 -
// San Miguel - Santiago - Chile
// contacto.pinayjara@gmail.com
// https://www.pinayjara.cl
// Creado, Programado y Diseñado por Piña y Jara
// Transportes y Servicios Ltda.


// -------------------------------------------------------------------------------------------------------
// ---------------------------------------- INICIO Piña y Jara medidor .JS -------------------------------
// -------------------------------------------------------------------------------------------------------

/*
medidor.js
----------
Actualiza en vivo, mientras se escribe, el medidor de fuerza de la contraseña (4 barras y lista de requisitos). Streamlit solo avisa al servidor cuando el
campo pierde el foco o se pulsa Enter, así que el medidor se calcula aquí, en el navegador, con la misma regla que herramientas/contrasenas.py.

Python antepone `var CFG = {...}` con la regla (requisitos, claves comunes, colores y texto de ayuda). El medidor de cada campo es un elemento con
`data-pj-medidor="<etiqueta del campo>"`; el campo se reconoce por su `aria-label`, que Streamlit toma de la etiqueta.
*/
(function () {
  var P;
  try { P = window.parent; } catch (e) { return; }
  var D = P.document;

  var DISFRAZ = { '@': 'a', '4': 'a', '3': 'e', '1': 'i', '!': 'i', '0': 'o', '$': 's', '5': 's', '7': 't' };
  var COMUNES = {};
  CFG.comunes.forEach(function (c) { COMUNES[c] = true; });
  var BORDES = /^[0-9!?#$%&*._\-+= ]+|[0-9!?#$%&*._\-+= ]+$/g;


  // TITULO SOLO LETRAS
  function soloLetras(texto) {
    return Array.from(texto).filter(function (c) { return /\p{L}/u.test(c); }).join('');
  }


  // TITULO ES COMUN
  function esComun(clave) {
    var minuscula = clave.toLowerCase();
    var nucleo = minuscula.replace(BORDES, '');
    var disfrazada = Array.from(nucleo).map(function (c) { return DISFRAZ[c] || c; }).join('');
    return !!COMUNES[soloLetras(disfrazada)] || !!COMUNES[soloLetras(minuscula)] || !!COMUNES[minuscula] || (minuscula.length > 0 && new Set(Array.from(minuscula)).size === 1);
  }


  // TITULO CUMPLIMIENTO
  function cumplimiento(clave) {
    var letras = Array.from(clave);
    return [
      letras.length >= 8,
      letras.some(function (c) { return c !== c.toLowerCase(); }),
      letras.some(function (c) { return c !== c.toUpperCase(); }),
      letras.some(function (c) { return /\p{Nd}/u.test(c); }),
      letras.some(function (c) { return /[^\p{L}\p{N}\s]/u.test(c); })
    ];
  }


  // TITULO DIBUJAR
  function dibujar(medidor, clave) {
    var cumple = cumplimiento(clave);
    var cumplidos = cumple.filter(Boolean).length;
    var llenas = [0, 1, 1, 2, 3, 4][cumplidos];
    var comun = clave !== '' && esComun(clave);
    if (!clave) llenas = 0;
    else if (comun) llenas = Math.min(llenas, 1);

    var barras = '';
    for (var i = 0; i < 4; i++) {
      var color = i < llenas ? CFG.colores[String(llenas)] : '#30363d';
      barras += "<span style='flex:1; height:4px; border-radius:2px; background:" + color + ";'></span>";
    }
    var detalle;
    if (!clave) {
      detalle = "<p style='color:#8b949e; font-size:12px; margin:4px 0 0;'>" + CFG.ayuda + "</p>";
    } else {
      var puntos = CFG.requisitos.map(function (texto, i) {
        return "<span style='color:" + (cumple[i] ? '#3fb950' : '#8b949e') + "; font-size:12px; margin-right:12px; white-space:nowrap;'>" +
               (cumple[i] ? '✓' : '○') + ' ' + texto + '</span>';
      }).join('');
      var aviso = comun ? "<p style='color:#f85149; font-size:12px; margin:4px 0 0;'>Esa contraseña es demasiado común.</p>" : '';
      detalle = "<div style='margin-top:4px; line-height:1.7;'>" + puntos + '</div>' + aviso;
    }
    medidor.innerHTML = "<div style='display:flex; gap:4px; margin-top:2px;'>" + barras + '</div>' + detalle;
  }


  // TITULO AL ESCRIBIR
  function alEscribir(evento) {
    var campo = evento.target;
    if (!campo || !campo.getAttribute) return;
    var etiqueta = campo.getAttribute('aria-label');
    if (!etiqueta) return;
    var medidor = D.querySelector('[data-pj-medidor="' + etiqueta.replace(/"/g, '\\"') + '"]');
    if (medidor) dibujar(medidor, campo.value || '');
  }

  // Cada ejecución de la página crea un componente nuevo: se quita el oyente anterior para no acumularlos.
  if (P.__pjMedidorOyente) D.removeEventListener('input', P.__pjMedidorOyente, true);
  P.__pjMedidorOyente = alEscribir;
  D.addEventListener('input', alEscribir, true);
})();

// -------------------------------------------------------------------------------------------------------
// ----------------------------------------- FIN Piña y Jara medidor .JS ---------------------------------
// -------------------------------------------------------------------------------------------------------

// Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
// Dirección: José Joaquín Prieto #5373 -
// San Miguel - Santiago - Chile
// contacto.pinayjara@gmail.com
// https://www.pinayjara.cl
// Creado, Programado y Diseñado por Piña y Jara
// Transportes y Servicios Ltda.
