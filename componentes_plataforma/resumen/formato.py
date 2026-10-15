"""Formateadores de la vista Resumen."""


def compact(x, moneda="", signo=False):
    """Formatea montos grandes de forma compacta (1.2M, 31.6K) y legible."""
    a = abs(x)
    s = ("+" if (signo and x > 0) else ("-" if x < 0 else ""))
    if a >= 1_000_000:
        cuerpo = f"{a/1_000_000:,.2f}M"
    elif a >= 10_000:
        cuerpo = f"{a/1_000:,.1f}K"
    else:
        cuerpo = f"{a:,.2f}"
    return f"{s}{cuerpo}" + (f" {moneda}" if moneda else "")


def vcls(x):
    return "rs-up" if x > 0 else ("rs-down" if x < 0 else "rs-neu")
