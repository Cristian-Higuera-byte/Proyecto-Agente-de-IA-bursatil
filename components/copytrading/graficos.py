"""Gráficos SVG sencillos de copy trading (como imágenes incrustadas): sparkline, dona de victorias y avatar."""
import base64
import math
import random


def spark(seed: str, w=150, h=44):
    rnd = random.Random(seed)
    n = 30
    v = 100.0
    pts = []
    for i in range(n):
        v += rnd.uniform(-1.5, 2.6)  # sesgo alcista
        pts.append(v)
    lo, hi = min(pts), max(pts)
    rng = (hi - lo) or 1
    coords = []
    for i, p in enumerate(pts):
        x = i * (w / (n - 1))
        y = h - 3 - (p - lo) / rng * (h - 6)
        coords.append(f"{x:.1f},{y:.1f}")
    linea = " ".join(coords)
    area = f"0,{h} " + linea + f" {w},{h}"
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}' viewBox='0 0 {w} {h}' "
           f"preserveAspectRatio='none'><defs><linearGradient id='g' x1='0' y1='0' x2='0' y2='1'>"
           f"<stop offset='0' stop-color='#3fb950' stop-opacity='0.30'/>"
           f"<stop offset='1' stop-color='#3fb950' stop-opacity='0'/></linearGradient></defs>"
           f"<polygon points='{area}' fill='url(#g)'/>"
           f"<polyline points='{linea}' fill='none' stroke='#3fb950' stroke-width='1.6'/></svg>")
    b64 = base64.b64encode(svg.encode()).decode()
    return f"<img src='data:image/svg+xml;base64,{b64}' width='{w}' height='{h}'>"


def donut(win_pct: float, size=180):
    r = size / 2 - 16
    cx = cy = size / 2
    circ = 2 * math.pi * r
    gan = circ * win_pct / 100
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{size}' height='{size}' viewBox='0 0 {size} {size}'>"
        f"<circle cx='{cx}' cy='{cy}' r='{r}' fill='none' stroke='#f85149' stroke-width='22'/>"
        f"<circle cx='{cx}' cy='{cy}' r='{r}' fill='none' stroke='#3fb950' stroke-width='22' "
        f"stroke-dasharray='{gan:.1f} {circ - gan:.1f}' stroke-dashoffset='{circ/4:.1f}' "
        f"transform='rotate(-90 {cx} {cy})' stroke-linecap='round'/></svg>"
    )
    b64 = base64.b64encode(svg.encode()).decode()
    return f"<img src='data:image/svg+xml;base64,{b64}' width='{size}' height='{size}'>"


def avatar(nombre: str) -> str:
    return "".join(p[0] for p in nombre.split()[:2]).upper()
