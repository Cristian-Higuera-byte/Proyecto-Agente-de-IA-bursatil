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

/** Oculta el contenido y lo vuelve a mostrar cuando Streamlit termina de dibujar la pantalla nueva (o a los 10 s, por si algo falla), de modo que no se vea el cambio a medias. */
function ocultarHastaTerminar() {
  const raiz = document.documentElement
  const app = document.querySelector('[data-testid="stApp"]')
  const direccionInicial = location.search
  const inicio = Date.now()
  raiz.classList.add(CLASE_CAMBIANDO)
  if (raiz.__pjCambiando) clearInterval(raiz.__pjCambiando)
  let corrio = false
  raiz.__pjCambiando = setInterval(function () {
    const estado = app ? app.getAttribute('data-test-script-state') : ''
    if (estado === 'running') corrio = true
    const cambio = corrio || location.search !== direccionInicial
    if ((cambio && estado !== 'running' && Date.now() - inicio > 250) || Date.now() - inicio > 10000) {
      clearInterval(raiz.__pjCambiando)
      raiz.__pjCambiando = null
      setTimeout(function () { raiz.classList.remove(CLASE_CAMBIANDO) }, 80)
    }
  }, 40)
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
