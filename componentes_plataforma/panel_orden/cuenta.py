"""
panel_orden/cuenta.py
---------------------
Lecturas de MetaTrader 5 que alimentan el ticket: info del símbolo, margen requerido,
margen libre y capital de la cuenta. Todo acotado por MT5_LOCK (acceso serializado).
Cada función devuelve None / valores neutros si MT5 no responde, para que la UI no falle.
"""
from proveedores.selector_mt5 import mt5  # type: ignore[import-untyped]

from herramientas.puente_mt5 import MT5_LOCK


def info_simbolo(real):
    """symbol_info del símbolo (dígitos, volúmenes, contrato...). None si no está."""
    try:
        with MT5_LOCK:
            mt5.symbol_select(real, True)
            return mt5.symbol_info(real)
    except Exception:
        return None


def margen(real, volumen, precio, tipo):
    """Margen requerido para una orden del lado `tipo` ('BUY'/'SELL'). None si falla."""
    try:
        action = mt5.ORDER_TYPE_BUY if tipo == "BUY" else mt5.ORDER_TYPE_SELL
        with MT5_LOCK:
            return mt5.order_calc_margin(action, real, float(volumen), float(precio))
    except Exception:
        return None


def margen_libre():
    """Margen libre de la cuenta (account_info().margin_free) o None."""
    try:
        with MT5_LOCK:
            cuenta = mt5.account_info()
        return float(cuenta.margin_free) if cuenta is not None else None
    except Exception:
        return None


def capital_cuenta():
    """Equity y moneda de la cuenta (base de la Calculadora de riesgo): (equity, moneda)."""
    try:
        with MT5_LOCK:
            cuenta = mt5.account_info()
        if cuenta is None:
            return None, "USD"
        return float(cuenta.equity), getattr(cuenta, "currency", "USD") or "USD"
    except Exception:
        return None, "USD"
