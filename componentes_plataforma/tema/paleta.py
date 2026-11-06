# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# --------------------------------------- INICIO Piña y Jara paleta .PY ---------------------------------
# -------------------------------------------------------------------------------------------------------

"""Paleta del tema azul de la plataforma: el cambio de colores de la gris-azulada original a un azul marino profundo con acentos azul eléctrico.

La plataforma tiene los colores escritos directamente en cientos de lugares (CSS, HTML, el gráfico). En vez de editar cada uno, `aplicar()` cambia el color viejo por el nuevo
en el texto que va al navegador (ver `componentes_plataforma/tema/__init__.py`). Para ajustar el tema basta con editar las tablas de este archivo. Solo se cambian los grises, azules y
fondos: los colores del mercado (verde que sube, rojo que baja), los de marca (naranja de los botones brillantes) y los morados del agente se dejan como están."""
from __future__ import annotations

import colorsys
import re
from functools import lru_cache

# Colores hexadecimales: el viejo (minúsculas) -> el nuevo.
HEX = {
    # --- fondos, del más oscuro al más claro ---
    "#0a0d14": "#040a1c", "#0b0f14": "#040a1c", "#0b0f19": "#040a1c", "#05080f": "#030817", "#05080e": "#030817",
    "#0d1117": "#050d24",      # fondo de la página y del gráfico
    "#0d131d": "#08173a", "#0f1620": "#0a1b40", "#111926": "#0b1b3a", "#141a22": "#0a1835", "#151c27": "#0b1a3b",
    "#161b22": "#0b1c42",      # tarjetas y paneles
    "#1b2430": "#0f2349", "#1f2937": "#12295a", "#202a37": "#10244b", "#21262d": "#112650", "#252f3d": "#15295a", "#263041": "#183063",
    "#2a2320": "#2a2320",
    # --- bordes y separadores ---
    "#30363d": "#1f3d86", "#2b3550": "#1d3772", "#2b3546": "#1d3772", "#3a4558": "#294a8c", "#3a3f47": "#294a8c", "#4a4f57": "#35569a",
    # --- textos ---
    "#e6edf3": "#eef4ff", "#c9d1d9": "#d3e0ff", "#d1d4dc": "#d6e2ff", "#8b949e": "#8ea6d4", "#9aa4b2": "#9bb2dc", "#9aa5b1": "#9bb2dc",
    "#6e7681": "#6f86b3", "#787b86": "#7a8fbd", "#6b7686": "#6c82b0", "#586174": "#5b70a0",
    # --- acentos azules ---
    "#58a6ff": "#3da5ff", "#1f6feb": "#2f6bff", "#2f81f7": "#3b82ff", "#3399ff": "#3da5ff",
}

# Colores rgb()/rgba(): (rojo, verde, azul) viejo -> nuevo.
RGB = {
    (13, 17, 23): (5, 13, 36), (22, 27, 34): (10, 24, 51), (48, 54, 61): (27, 50, 112), (88, 166, 255): (61, 165, 255),
    (139, 148, 158): (142, 166, 212), (230, 237, 243): (238, 244, 255), (56, 139, 253): (59, 130, 255), (31, 111, 235): (47, 107, 255),
    (80, 88, 100): (91, 112, 160), (5, 8, 15): (3, 8, 23), (5, 8, 14): (3, 8, 23), (10, 13, 20): (4, 10, 28), (1, 4, 9): (2, 6, 20),
}

# TITULO COLOR AUTOMATICO

@lru_cache(maxsize=None)
def _automatico(hexa: str) -> str | None:
    """Color nuevo para un gris/azul oscuro que no está en las tablas (devuelve None si no corresponde cambiarlo).

    Cambia solo los colores casi neutros o azulados: los fondos oscuros pasan a un azul marino de la misma claridad y los textos grises a un azul grisáceo claro. Los verdes, rojos, naranjas,
    morados y amarillos (colores del mercado y de la marca), el blanco y el negro no se tocan."""
    r, g, b = (int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    grados = h * 360
    if not 0.025 < l < 0.93 or s > 0.45 or not (s < 0.10 or 195 <= grados <= 255):
        return None
    if l < 0.30:
        nh, ns, nl = 222 / 360, 0.66 - 0.45 * l, l * 0.95            # fondos y bordes oscuros -> azul marino
    elif l < 0.60:
        nh, ns, nl = 220 / 360, 0.34, l                               # grises medios -> azul grisáceo
    else:
        nh, ns, nl = 218 / 360, 0.50, min(0.95, l + 0.01)             # textos claros -> azul muy claro
    nr, ng, nb = colorsys.hls_to_rgb(nh, nl, ns)
    return "#%02x%02x%02x" % (round(nr * 255), round(ng * 255), round(nb * 255))


# Naranjas de la marca -> azules brillantes (la marca pasa a azul eléctrico). Los que no estén aquí se calculan según su claridad (ver `_naranja_a_azul`).
NARANJA_HEX = {
    "#ff8f00": "#3da5ff", "#ff6b35": "#2f6bff", "#ff6a3d": "#2f6bff", "#ffb21a": "#5ab8ff", "#ffa01a": "#5ab8ff", "#ff9a6b": "#8fc3ff", "#ffb067": "#8fc3ff", "#ffc58a": "#b5d8ff",
    "#2a2320": "#1b3270", "#3a2a22": "#1d3d85",       # bordes marrón oscuro de las tarjetas con acento naranja
}
# Rojos que, dentro de un degradado con naranja, son parte del degradado de la marca y pasan a azul profundo.
ROJOS_DE_MARCA = {"#ff4b4b": "#1f4fff", "#ff3d3d": "#1f4fff", "#ff5c5c": "#2a5cff"}
# rgb()/rgba() naranja de la marca (sombras, resplandores, fondos translúcidos) -> azul.
NARANJA_RGB = {(255, 107, 53): (47, 107, 255), (255, 143, 0): (61, 165, 255), (255, 110, 0): (47, 107, 255), (255, 75, 75): (31, 79, 255), (255, 160, 26): (90, 184, 255)}
# Una regla CSS cuyo selector contenga alguno de estos textos CONSERVA sus naranjas: la burbuja y los paneles del agente, y el color propio del plan Profesional.
PROTEGIDOS = ("agente", "agp_", "pj-chat", "pj_chat", "chat_burbuja", ".vp-pro", ".vp-destacada", "vpc_pro", ".vp-cinta")
# Animaciones (@keyframes) que conservan sus naranjas: el latido del agente y el aura del plan Profesional.
KEYFRAMES_PROTEGIDOS = ("ag-pulso", "vp-aura")

# Un color hexadecimal de 6 cifras (y opcionalmente 2 más de transparencia), que no sea parte de una entidad HTML ni de otra palabra.
_RE_HEX = re.compile(r"(?<![&\w#])#([0-9a-fA-F]{6})([0-9a-fA-F]{2})?(?![0-9a-zA-Z])")
# rgb() o rgba() con números enteros.
_RE_RGB = re.compile(r"(rgba?\(\s*)(\d{1,3})(\s*,\s*)(\d{1,3})(\s*,\s*)(\d{1,3})")


# TITULO CAMBIAR HEX

def _cambiar_hex(m: re.Match) -> str:
    """Reemplazo de un color hexadecimal: si está en la tabla se cambia (conservando la transparencia); si no, se deja igual."""
    clave = "#" + m.group(1).lower()
    nuevo = HEX.get(clave) or _automatico(clave)
    return m.group(0) if nuevo is None else nuevo + (m.group(2) or "")


# TITULO CAMBIAR RGB

def _cambiar_rgb(m: re.Match) -> str:
    """Reemplazo de un color rgb()/rgba(): si la terna está en la tabla se cambia (conservando lo que sigue, como la transparencia); si no, se deja igual."""
    terna = (int(m.group(2)), int(m.group(4)), int(m.group(6)))
    nuevo = RGB.get(terna)
    if nuevo is None:
        auto = _automatico("#%02x%02x%02x" % terna) if max(terna) <= 255 else None
        nuevo = tuple(int(auto[i:i + 2], 16) for i in (1, 3, 5)) if auto else None
    if nuevo is None:
        return m.group(0)
    return f"{m.group(1)}{nuevo[0]}{m.group(3)}{nuevo[1]}{m.group(5)}{nuevo[2]}"


# TITULO NARANJA A AZUL

@lru_cache(maxsize=None)
def _naranja_a_azul(hexa: str, en_degradado: bool = False) -> str | None:
    """Azul que reemplaza a un color naranja de la marca (None si el color no es naranja de marca). Dentro de un degradado, los rojos de marca también pasan a azul.

    Un naranja de marca es un color de tono entre 8° y 45° y saturación casi total; los amarillos de aviso (menos saturados) y los rojos del mercado no se tocan."""
    if hexa in NARANJA_HEX:
        return NARANJA_HEX[hexa]
    if en_degradado and hexa in ROJOS_DE_MARCA:
        return ROJOS_DE_MARCA[hexa]
    r, g, b = (int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    if not (8 <= h * 360 <= 45 and s >= 0.95 and 0.42 <= l <= 0.86):
        return None
    t = min(1.0, max(0.0, (l - 0.45) / 0.40))                                    # 0 = naranja oscuro, 1 = naranja claro
    c0, c1 = (0x2f, 0x6b, 0xff), (0x8f, 0xc3, 0xff)                              # del azul eléctrico al azul claro
    return "#%02x%02x%02x" % tuple(round(x0 + (x1 - x0) * t) for x0, x1 in zip(c0, c1))


# Degradado (linear, radial o cónico) con un nivel de paréntesis anidado como máximo (por ejemplo, con rgba() dentro).
_RE_DEGRADADO = re.compile(r"(?:linear|radial|conic)-gradient\((?:[^()]|\([^()]*\))*\)")
# Regla CSS más interna: selector y cuerpo. Un bloque @keyframes se trata aparte.
_RE_REGLA = re.compile(r"([^{}]*)\{([^{}]*)\}")
_RE_KEYFRAMES = re.compile(r"(@keyframes\s+([\w-]+)\s*\{)((?:[^{}]|\{[^{}]*\})*)\}")


# TITULO NARANJA EN TEXTO

def _naranja_en(texto: str, rojos_solos: bool = False) -> str:
    """Cambia a azul todos los naranjas de la marca de `texto` (hexadecimales y rgba), incluidos los rojos de marca dentro de degradados con naranja. `rojos_solos` cambia también los
    rojos de marca fuera de degradados (para los botones primarios con el rojo de Streamlit)."""
    def _degradado(m: re.Match) -> str:
        g = m.group(0)
        hexas = [x.lower() for x in re.findall(r"#[0-9a-fA-F]{6}(?![0-9a-zA-Z])", g)]
        rgbs = [(int(a), int(b), int(c)) for a, b, c in re.findall(r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})", g)]
        if not (any(_naranja_a_azul(x) for x in hexas) or any(r in NARANJA_RGB and r != (255, 75, 75) for r in rgbs)):
            return g
        def _hex(h: re.Match) -> str:
            nuevo = _naranja_a_azul("#" + h.group(1).lower(), True)
            return h.group(0) if nuevo is None else nuevo + (h.group(2) or "")
        return _RE_HEX.sub(_hex, g)

    texto = _RE_DEGRADADO.sub(_degradado, texto)

    def _solido(m: re.Match) -> str:
        nuevo = _naranja_a_azul("#" + m.group(1).lower(), rojos_solos)
        return m.group(0) if nuevo is None else nuevo + (m.group(2) or "")
    texto = _RE_HEX.sub(_solido, texto)

    def _rgb(m: re.Match) -> str:
        nuevo = NARANJA_RGB.get((int(m.group(2)), int(m.group(4)), int(m.group(6))))
        return m.group(0) if nuevo is None else f"{m.group(1)}{nuevo[0]}{m.group(3)}{nuevo[1]}{m.group(5)}{nuevo[2]}"
    return _RE_RGB.sub(_rgb, texto)


# TITULO NARANJA EN CSS

def _naranja_en_css(texto: str) -> str:
    """Pasa a azul los naranjas de un texto con CSS, respetando las reglas protegidas (agente y plan Profesional) y las animaciones protegidas."""
    guardados: list[str] = []

    def _keyframes(m: re.Match) -> str:
        bloque = m.group(0) if m.group(2) in KEYFRAMES_PROTEGIDOS else m.group(1) + _naranja_en(m.group(3)) + "}"
        guardados.append(bloque)
        return f"\x00{len(guardados) - 1}\x00"

    def _regla(m: re.Match) -> str:
        selector, cuerpo = m.group(1), m.group(2)
        bajo = re.sub(r"/\*.*?\*/", "", selector, flags=re.S).lower()   # los comentarios que preceden al selector no cuentan
        if any(p in bajo for p in PROTEGIDOS) and not ("button" in bajo and "vpc_pro" in bajo):
            return m.group(0)
        protegido = any(p in bajo for p in PROTEGIDOS) and not ("button" in bajo and "vpc_pro" in bajo)
        if "<" in bajo and "style" in bajo and not protegido:        # HTML con colores en línea que quedó pegado antes de una regla
            selector = _naranja_en(selector)
        return f"{selector}{{{_naranja_en(cuerpo, rojos_solos='primary' in bajo)}}}"

    sin_animaciones = _RE_KEYFRAMES.sub(_keyframes, texto)
    resultado = _RE_REGLA.sub(_regla, sin_animaciones)
    return re.sub(r"\x00(\d+)\x00", lambda m: guardados[int(m.group(1))], resultado)


# TITULO APLICAR

@lru_cache(maxsize=512)
def aplicar(texto: str, naranja: bool = True) -> str:
    """Devuelve `texto` (CSS, HTML o JavaScript) con los colores de la paleta vieja cambiados por los del tema azul. Se recuerda el resultado de los textos ya vistos.

    Los grises y azules siempre cambian. Los naranjas de la marca pasan a azul brillante cuando `naranja` es verdadero (el valor por defecto); con `naranja=False` se conservan: es lo que
    usan los marcos del navegador (gráfico, scripts), donde el naranja tiene significado propio (línea de stop loss, colores de dibujo)."""
    if "#" not in texto and "rgb" not in texto:
        return texto
    texto = _RE_RGB.sub(_cambiar_rgb, _RE_HEX.sub(_cambiar_hex, texto))
    if not naranja:
        return texto
    return _naranja_en_css(texto) if "{" in texto else _naranja_en(texto)


# -------------------------------------------------------------------------------------------------------
# ----------------------------------------- FIN Piña y Jara paleta .PY ----------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
