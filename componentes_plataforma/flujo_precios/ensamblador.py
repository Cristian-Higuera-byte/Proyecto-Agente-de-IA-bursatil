# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ---------------------------------- INICIO Piña y Jara ensamblador .PY ---------------------------------
# -------------------------------------------------------------------------------------------------------

"""Ensambla el script del feed en vivo a partir de los fragmentos de `js/` (en orden alfabético: 00_, 10_…).
Todos viven dentro de una misma función autoejecutable, así que comparten variables; por eso solo se cortan
por responsabilidad, no se pueden cargar por separado. Se relee solo si algún archivo cambia en disco."""
import json
from pathlib import Path

# Lector de archivos estáticos con caché que se invalida al cambiar el archivo en disco.
from componentes_plataforma._estaticos import texto
from componentes_plataforma.canal_cuenta import canal_de_la_sesion

# Carpeta con los fragmentos JS del feed.
_JS_DIR = Path(__file__).parent / "js"


# TITULO SCRIPT FLUJO

def script_flujo(api_url: str) -> str:
    """HTML (<script>…</script>) del feed en vivo apuntando a `api_url`.

    Lee y concatena todos los `js/*.js` en orden alfabético (00_, 10_, ...), los envuelve en una etiqueta
    script y sustituye el marcador `__API__` por la URL del servidor de datos serializada como cadena JSON
    (así queda correctamente escapada) y `__CANAL__` por el secreto del canal privado de la cuenta de esta sesión (componentes_plataforma/canal_cuenta.py).
    No tiene efectos secundarios más allá de leer archivos.
    """
    # Une los fragmentos en orden: todos forman una sola función autoejecutable.
    cuerpo = "".join(texto(f) for f in sorted(_JS_DIR.glob("*.js")))
    # Envuelve en <script> y reemplaza el marcador de la URL del servidor.
    return ("\n<script>\n" + cuerpo + "</script>\n").replace("__API__", json.dumps(api_url)).replace("__CANAL__", json.dumps(canal_de_la_sesion()))


# -------------------------------------------------------------------------------------------------------
# ----------------------------------- FIN Piña y Jara ensamblador .PY -----------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
