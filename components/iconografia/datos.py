"""Datos de los íconos (monedas, criptos, índices, bolsas, materias primas…). Viven en `datos/*.json`;
aquí se leen una vez y quedan listos con el mismo formato que usaba el código."""
import base64
from pathlib import Path

from components._estaticos import datos_json

_DIR = Path(__file__).parent / "datos"


def _json(nombre: str):
    return datos_json(_DIR / nombre)


def svg_circulo(fondo: str, figura: str) -> str:
    """Círculo de color con una figura blanca, como imagen data-URI."""
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
        f"<circle cx='16' cy='16' r='16' fill='{fondo}'/>{figura}</svg>"
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


_URLS = _json("urls.json")
FLAG = _URLS["bandera"]                    # banderas redondas (circle-flags)
CRIPTO_URL = _URLS["cripto"]               # logos de cripto (cryptocurrency-icons)
LOGO_ACCION = _URLS["logo_accion"]         # logos de acciones/ETF

MONEDA_PAIS = _json("moneda_pais.json")    # moneda -> código de bandera
CRIPTOS = _json("criptos.json")            # cripto -> archivo del logo
INDICES = {k: tuple(v) for k, v in _json("indices.json").items()}   # núcleo -> (bandera, etiqueta)
PALETA = _json("paleta.json")              # colores estables para las iniciales
RIC_A_TICKER = _json("ric_a_ticker.json")  # excepciones RIC de Reuters -> ticker del logo

_BOLSAS = _json("bolsas.json")
BOLSA_SUFIJO = _BOLSAS["sufijo"]                      # bolsa Reuters -> sufijo de la fuente de logos
BOLSAS_CLASE = set(_BOLSAS["clase_minuscula"])        # nórdicas: clase de acción en minúscula
BOLSAS_MENOS_UNA = set(_BOLSAS["menos_una_letra"])    # Viena/Helsinki: el RIC agrega 1 letra

_FIGURAS = _json("figuras.json")
MATERIAS = {k: svg_circulo(c, _FIGURAS[f]) for k, (c, f) in _json("materias.json").items()}
GENERICO = {k: svg_circulo(c, _FIGURAS[f]) for k, (c, f) in _json("genericos.json").items()}
