"""Normalización de tickets entre brókers.

MT5 identifica posiciones y órdenes con enteros; Capital.com con un dealId de texto.
`ticket()` conserva el entero cuando el valor es numérico y deja el texto tal cual si no,
para no romper nada con `int()` según el proveedor activo."""


def ticket(valor):
    """Devuelve el ticket como int (si es numérico) o como str (dealId de Capital.com).

    Recibe int, float, str o None; None se devuelve sin cambios."""
    if valor is None:
        return None
    t = str(valor).strip()
    if t.endswith(".0"):
        t = t[:-2]
    return int(t) if t.isdigit() else t
