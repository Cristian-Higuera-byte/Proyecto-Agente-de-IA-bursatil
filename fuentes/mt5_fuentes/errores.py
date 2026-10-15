"""Errores de la fuente MT5."""


class ErrorMT5(Exception):
    """Fallo de la fuente MT5."""


class OperacionNoPermitida(ErrorMT5, AttributeError):
    """Se intentó usar una función de MT5 vetada (solo lectura)."""
