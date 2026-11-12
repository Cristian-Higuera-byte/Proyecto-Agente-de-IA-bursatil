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

// [acceso] Navegación sin recargar entre la portada, el inicio de sesión, el registro y «Olvidé mi contraseña», y entre las opciones del menú del usuario (Perfil,
// Configuración, cuentas) una vez iniciada la sesión (Streamlit CCv2). Python le dice qué enlaces atender (`data.prefijos`, y `data.portada` para el enlace `./`).
// Esas pantallas se enlazaban con enlaces normales (`?acceso=entrar`), que recargan toda la página y dejan ver el esqueleto gris de Streamlit mientras vuelve a arrancar.
// Este componente intercepta el clic en esos enlaces, evita la recarga y le avisa a Python (setTriggerValue «destino») a dónde ir; Python cambia la dirección y dibuja la
// pantalla nueva en la misma sesión. Un clic con Ctrl, Mayús o botón medio sigue funcionando como siempre (abre en otra pestaña).

/** ¿Es un enlace interno que se abre en la misma pestaña y empieza con alguno de los prefijos indicados (o es la portada `./`, si se permite)? */
function esEnlaceInterno(enlace, prefijos, portada) {
  const destino = enlace.getAttribute('href') || ''
  if (enlace.target && enlace.target !== '_self') return false
  if (portada && destino === './') return true
  return prefijos.some(function (prefijo) { return destino.indexOf(prefijo) === 0 })
}

export default function (component) {
  const { setTriggerValue, data } = component
  const prefijos = (data && data.prefijos) || ['?acceso=']
  const portada = !data || data.portada !== false

  /** Al pulsar un enlace de acceso: cancela la recarga y entrega a Python la dirección de destino. */
  function alPulsar(evento) {
    if (evento.defaultPrevented || evento.button !== 0 || evento.metaKey || evento.ctrlKey || evento.shiftKey || evento.altKey) return
    const enlace = evento.target && evento.target.closest ? evento.target.closest('a') : null
    if (!enlace || !esEnlaceInterno(enlace, prefijos, portada)) return
    evento.preventDefault()
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
