"""Datos del símbolo según MetaTrader 5 (carpeta y código bursátil), con caché."""
import re

_INFO_CACHE: dict = {}


def info_mt5(simbolo: str) -> tuple:
    """(carpeta, ric) del símbolo según MT5. carpeta = primer nivel de `path`
    ("Stocks", "ETF Derivatives", "Cryptocurrencies"…); ric = código entre
    paréntesis al final de la descripción ("Adidas AG (ADSGn.DE)" -> "ADSGn.DE",
    "Telus Corp (TU)" -> "TU"). ("", "") si no hay MT5.
    Hallazgo: XM nombra las acciones por la empresa ("Adidas", "Nvidia"), sin
    sufijo de bolsa; el código bursátil solo está en la descripción."""
    if simbolo in _INFO_CACHE:
        return _INFO_CACHE[simbolo]
    res = ("", "")
    try:
        from proveedores.selector_mt5 import mt5  # type: ignore[import-untyped]
        from herramientas.puente_mt5 import MT5_LOCK, resolver_simbolo
        with MT5_LOCK:
            info = mt5.symbol_info(resolver_simbolo(simbolo))
        if info is not None:
            carpeta = (info.path or "").split(chr(92))[0]
            m = re.search(r"\(([A-Za-z0-9_]+(?:\.[A-Za-z]{1,3})?)\)\s*$", info.description or "")
            res = (carpeta, m.group(1) if m else "")
            _INFO_CACHE[simbolo] = res     # solo se guarda si MT5 respondió
    except Exception:
        pass
    return res
