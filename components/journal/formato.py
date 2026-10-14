"""Formateadores del Diario."""


def dur(seg):
    seg = int(seg or 0)
    d, seg = divmod(seg, 86400)
    h, seg = divmod(seg, 3600)
    mn = seg // 60
    if d:
        return f"{d}d {h}h"
    if h:
        return f"{h}h {mn}m"
    return f"{mn}m"


def factor(x):
    return "∞" if x == float("inf") else f"{x:,.2f}"


def updn(x):
    return "up" if (x or 0) >= 0 else "down"
