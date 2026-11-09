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
   ------------------------------------ INICIO Piña y Jara navegacion .JS --------------------------------
   ------------------------------------------------------------------------------------------------------- */

// [acceso] Navegación sin recargar entre la portada, el inicio de sesión, el registro y «Olvidé mi contraseña» (Streamlit CCv2).
// Esas pantallas se enlazaban con enlaces normales (`?acceso=entrar`), que recargan toda la página y dejan ver el esqueleto gris de Streamlit mientras vuelve a arrancar.
// Este componente intercepta el clic en esos enlaces, evita la recarga y le avisa a Python (setTriggerValue «destino») a dónde ir; Python cambia la dirección y dibuja la
// pantalla nueva en la misma sesión. Un clic con Ctrl, Mayús o botón medio sigue funcionando como siempre (abre en otra pestaña).

/** ¿Es un enlace interno de acceso (`?acceso=...` o la portada `./`) que se abre en la misma pestaña? */
function esEnlaceDeAcceso(enlace) {
  const destino = enlace.getAttribute('href') || ''
  if (enlace.target && enlace.target !== '_self') return false
  return destino.indexOf('?acceso=') === 0 || destino === './'
}

// Clase que oculta el contenido mientras se cambia de pantalla (ver navegacion.css).
const CLASE_CAMBIANDO = 'pj-acceso-cambiando'
// Tiempo sin cambios en la pantalla (ms) que se exige antes de mostrarla, y tiempo máximo (ms) que puede quedar oculta si algo falla.
const QUIETUD_MS = 400
const MAXIMO_MS = 10000

/** ¿Está la pantalla nueva realmente lista? Streamlit terminó de ejecutar, no quedan elementos de la pantalla anterior ni esqueletos, y los campos ya tienen su `input` (los campos
 *  se cargan por separado y, mientras llegan, se ve solo la etiqueta). */
function pantallaLista(app) {
  if (app && app.getAttribute('data-test-script-state') === 'running') return false
  if (document.querySelector('[data-stale="true"], [data-testid="stSkeleton"], [class*="Skeleton"]')) return false
  const campos = document.querySelectorAll('[data-testid="stTextInput"], [data-testid="stSelectbox"], [data-testid="stTextArea"]')
  for (let i = 0; i < campos.length; i++) {
    if (!campos[i].querySelector('input, textarea')) return false
  }
  return true
}

/** Oculta el contenido y lo vuelve a mostrar cuando la pantalla nueva está lista y quieta (o a los 10 s, por si algo falla), de modo que no se vea el cambio a medias. */
function ocultarHastaTerminar() {
  const raiz = document.documentElement
  const app = document.querySelector('[data-testid="stApp"]')
  const direccionInicial = location.search
  const inicio = Date.now()
  let ultimoCambio = Date.now()
  let corrio = false
  raiz.classList.add(CLASE_CAMBIANDO)
  if (raiz.__pjCambiando) { clearInterval(raiz.__pjCambiando.reloj); raiz.__pjCambiando.observador.disconnect() }
  // Cada vez que cambia algo en la pantalla se reinicia la cuenta de «quietud».
  const observador = new MutationObserver(function () { ultimoCambio = Date.now() })
  observador.observe(document.body, { childList: true, subtree: true, attributes: true })
  function terminar() {
    clearInterval(reloj)
    observador.disconnect()
    raiz.__pjCambiando = null
    setTimeout(function () { raiz.classList.remove(CLASE_CAMBIANDO) }, 60)
  }
  const reloj = setInterval(function () {
    if (app && app.getAttribute('data-test-script-state') === 'running') corrio = true
    const cambio = corrio || location.search !== direccionInicial
    const quieta = Date.now() - ultimoCambio >= QUIETUD_MS
    if ((cambio && Date.now() - inicio > 250 && quieta && pantallaLista(app)) || Date.now() - inicio > MAXIMO_MS) terminar()
  }, 40)
  raiz.__pjCambiando = { reloj: reloj, observador: observador }
}

export default function (component) {
  const { setTriggerValue } = component

  /** Al pulsar un enlace de acceso: cancela la recarga, oculta el contenido y entrega a Python la dirección de destino. */
  function alPulsar(evento) {
    if (evento.defaultPrevented || evento.button !== 0 || evento.metaKey || evento.ctrlKey || evento.shiftKey || evento.altKey) return
    const enlace = evento.target && evento.target.closest ? evento.target.closest('a') : null
    if (!enlace || !esEnlaceDeAcceso(enlace)) return
    evento.preventDefault()
    ocultarHastaTerminar()
    setTriggerValue('destino', enlace.getAttribute('href'))
  }

  document.addEventListener('click', alPulsar, true)
  return function limpiar() {
    document.removeEventListener('click', alPulsar, true)
  }
}

/* -------------------------------------------------------------------------------------------------------
   ------------------------------------- FIN Piña y Jara navegacion .JS ----------------------------------
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
