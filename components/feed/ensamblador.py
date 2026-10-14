"""Ensambla el script del feed en vivo a partir de los fragmentos de `js/` (en orden alfabético: 00_, 10_…).
Todos viven dentro de una misma función autoejecutable, así que comparten variables; por eso solo se cortan
por responsabilidad, no se pueden cargar por separado. Se relee solo si algún archivo cambia en disco."""
import json
from pathlib import Path

from components._estaticos import texto

_JS_DIR = Path(__file__).parent / "js"


def script_feed(api_url: str) -> str:
    """HTML (<script>…</script>) del feed en vivo apuntando a `api_url`."""
    cuerpo = "".join(texto(f) for f in sorted(_JS_DIR.glob("*.js")))
    return ("\n<script>\n" + cuerpo + "</script>\n").replace("__API__", json.dumps(api_url))
