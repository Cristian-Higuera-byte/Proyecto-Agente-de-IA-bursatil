"""JS de trading desde el gráfico: se ensambla a partir de los fragmentos de js/ (orden alfabético 00_, 10_…).
Todos viven dentro de una misma función autoejecutable (la que central_panel/grafico insertan DENTRO de
`iniciar()` del gráfico), por eso solo se cortan por responsabilidad."""
import json
from pathlib import Path

from componentes_plataforma._estaticos import texto
from componentes_plataforma.posiciones.datos_iniciales import iniciales
from herramientas.puente_mt5 import resolver_simbolo

_JS_DIR = Path(__file__).parent / "js"


def js_posiciones(simbolo: str) -> str:
    """JS de trading desde el gráfico para el símbolo cargado."""
    real = resolver_simbolo(simbolo)
    js = "\n" + "".join(texto(f) for f in sorted(_JS_DIR.glob("*.js")))
    return (js.replace("__POS_REAL__", json.dumps(real))
              .replace("__POS_INI__", json.dumps(iniciales(real))))
