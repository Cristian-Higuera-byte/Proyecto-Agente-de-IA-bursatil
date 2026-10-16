"""Entrada de un símbolo para la watchlist (nombre, categoría, precio y variación)."""
from proveedores.selector_mt5 import mt5  # type: ignore[import-untyped]

from componentes_plataforma.mercado_datos.referencias import variacion
from herramientas import gestor_lista_activos as wl
from herramientas.puente_mt5 import MT5_LOCK, obtener_precio_actual, resolver_simbolo


def construir_entrada(simbolo: str) -> dict:
    """Arma la entrada de un símbolo para la watchlist (nombre, categoría, precio)
    usando el nombre EXACTO de MT5 (sin limpiar los '...')."""
    try:
        sim_real = resolver_simbolo(simbolo)  # nombre real en ESTE terminal (con/sin '...')
        with MT5_LOCK:
            mt5.symbol_select(sim_real, True)
            info = mt5.symbol_info(sim_real)
    except Exception:
        info = None
    nombre = (info.description if info and getattr(info, "description", "") else wl.nombre_visible(simbolo))
    mercado = wl.categoria_simbolo(getattr(info, "path", "") if info else "", simbolo)
    precio = 0.0
    try:
        tick = obtener_precio_actual(simbolo)
        if "error" not in tick:
            precio = tick.get("last", 0) if tick.get("last", 0) > 0 else tick.get("bid", 0)
    except Exception:
        pass
    var = variacion(simbolo, float(precio or 0.0), 2 if precio > 100 else 5)
    return {
        "nombre": nombre,
        "mercado": mercado,
        "precio": float(precio or 0.0),
        "var": var[0] if var else "+0.00 (0.00%)",
        "sube": var[1] if var else True,
    }
