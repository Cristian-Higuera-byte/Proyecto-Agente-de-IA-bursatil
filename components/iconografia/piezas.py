"""Piezas HTML de los íconos: cajas, imágenes circulares, pares de banderas, índices, iniciales y logos."""
import html
import re
import zlib

from components.iconografia.datos import FLAG, PALETA, svg_circulo


def caja(s: int, interior: str, ancho: int | None = None) -> str:
    w = ancho or s
    return (
        f"<span style='position:relative; display:inline-block; flex:0 0 {w}px; "
        f"width:{w}px; height:{s}px; vertical-align:middle;'>{interior}</span>"
    )


def img(src: str, d: int, left: float, top: float, z: int = 1, borde: bool = False,
        fondo: str = "transparent") -> str:
    aro = "box-shadow:0 0 0 1.5px #0d1117;" if borde else ""
    return (
        f"<img src='{src}' alt='' style='position:absolute; left:{left:.1f}px; top:{top:.1f}px; "
        f"width:{d}px; height:{d}px; border-radius:50%; z-index:{z}; background:{fondo}; "
        f"object-fit:cover; {aro}'>"
    )


def iniciales(texto: str, s: int, z: int = 0) -> str:
    t = re.sub(r"[^A-Za-z0-9]", "", texto)[:2].upper() or "?"
    color = PALETA[zlib.crc32(texto.encode()) % len(PALETA)]
    return (
        f"<span style='position:absolute; inset:0; border-radius:50%; background:{color}; "
        f"color:#fff; font-weight:800; font-size:{max(9, int(s * 0.38))}px; z-index:{z}; "
        f"display:flex; align-items:center; justify-content:center; "
        f"font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;'>{html.escape(t)}</span>"
    )


def par(src_a: str, src_b: str, s: int) -> str:
    """Dos círculos superpuestos: A adelante-izquierda, B atrás-derecha."""
    d = round(s * 0.66)
    top = (s - d) / 2
    return caja(s, img(src_b, d, s - d, top, z=1) + img(src_a, d, 0, top, z=2, borde=True))


def indice(pais: str, etiqueta: str, s: int) -> str:
    d = round(s * 0.84)
    fs = max(6, round(s * 0.2))
    badge = (
        f"<span style='position:absolute; left:50%; bottom:-1px; transform:translateX(-50%); "
        f"z-index:3; background:#11151c; color:#e6edf3; font-size:{fs}px; font-weight:700; "
        f"line-height:1; padding:1px 3px; border-radius:3px; white-space:nowrap; "
        f"font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;'>{etiqueta}</span>"
    )
    return caja(s, img(FLAG.format(pais), d, (s - d) / 2, 0, z=1) + badge)


def logo(url: str, s: int) -> str:
    """Logo COMPLETO dentro de un círculo blanco (object-fit: contain + margen).
    Hallazgo: con 'cover' los logos apaisados (Adidas 128×86) se recortaban al
    centro y el círculo quedaba en blanco."""
    m = max(2, round(s * 0.14))
    return (
        f"<span style='position:absolute; inset:0; border-radius:50%; background:#ffffff; "
        f"overflow:hidden; display:flex; align-items:center; justify-content:center;'>"
        f"<img src='{url}' alt='' style='width:{s - 2 * m}px; height:{s - 2 * m}px; "
        f"object-fit:contain;'></span>"
    )


def svg_iniciales(texto: str) -> str:
    """Círculo con iniciales como imagen (para combinarlo en `par`)."""
    t = html.escape(re.sub(r"[^A-Za-z0-9]", "", texto)[:3].upper() or "?")
    color = PALETA[zlib.crc32(texto.encode()) % len(PALETA)]
    fs = 11 if len(t) <= 2 else 9
    figura = (f"<text x='16' y='16' text-anchor='middle' dominant-baseline='central' "
              f"font-family='Arial,sans-serif' font-weight='700' font-size='{fs}' fill='#fff'>{t}</text>")
    return svg_circulo(color, figura)
