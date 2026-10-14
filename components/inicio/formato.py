"""Pequeños formateadores de la vista Inicio."""


def fmt(v, dec=2):
    try:
        return f"${float(v):,.{dec}f}"
    except Exception:
        return "—"


def mi(nombre: str, color: str = "", size: int = 0) -> str:
    estilo = (f"color:{color};" if color else "") + (f"font-size:{size}px;" if size else "")
    return f"<span class='mi' style='{estilo}'>{nombre}</span>"


def estado_margen(ml: float) -> tuple:
    """(texto, color) del semáforo del nivel de margen."""
    if not ml:
        return "Sin posiciones", "#8b949e"
    if ml >= 300:
        return "Saludable", "#3fb950"
    if ml >= 150:
        return "Atención", "#d29922"
    return "Riesgo", "#f85149"
