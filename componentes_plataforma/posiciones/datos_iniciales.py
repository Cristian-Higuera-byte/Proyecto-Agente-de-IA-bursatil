"""Posiciones y órdenes del símbolo con el formato del feed, más volumen mínimo, distancia mínima y desfase horario."""
import time

import MetaTrader5 as mt5  # type: ignore[import-untyped]

from herramientas import almacen_oco, almacen_stop_dinamico
from herramientas.puente_mt5 import MT5_LOCK, inicializar_mt5


def iniciales(real: str) -> dict:
    """Posiciones y órdenes del símbolo con el mismo formato que el feed
    (`acc.pi` / `acc.ord`), más volumen mínimo, distancia mínima y desfase horario.
    OJO: solo datos ESTABLES. Si algo cambiara a cada segundo (Bid/Ask, P/G), el
    HTML del gráfico sería distinto en cada rerun y Streamlit recargaría el iframe
    (se perdería el zoom). Bid/Ask y P/G llegan en vivo por el feed."""
    out = {"pos": {}, "ord": {}, "ba": [0, 0], "vmin": 0.01, "sm": 0.0, "k": 0.0, "off": 0, "em": 0}
    try:
        if not inicializar_mt5():
            return out
        with MT5_LOCK:
            mt5.symbol_select(real, True)
            posiciones = mt5.positions_get(symbol=real) or []
            ordenes = mt5.orders_get(symbol=real) or []
            si = mt5.symbol_info(real)
            tick = mt5.symbol_info_tick(real)
        ts = float(getattr(si, "trade_tick_size", 0) or 0)
        k = (float(si.trade_tick_value) / ts) if si and ts else 0.0
        sm = float(getattr(si, "trade_stops_level", 0) or 0) * float(getattr(si, "point", 0) or 0)
        out.update(sm=sm, k=k, vmin=float(getattr(si, "volume_min", 0.01) or 0.01),
                   em=int(getattr(si, "expiration_mode", 0) or 0))   # 1 GTC · 2 DAY · 4 fecha
        if tick is not None:
            # hora del servidor del bróker − hora real (s), redondeado a 15 min: caducidad por fecha
            out["off"] = round((int(tick.time) - time.time()) / 900) * 900
        tr = almacen_stop_dinamico.leer()      # tickets con stop dinámico activo
        oco_tks = almacen_oco.tickets_en_oco()   # tickets vinculados en un par OCO
        for p in posiciones:
            out["pos"][str(p.ticket)] = {
                "s": p.symbol, "t": int(p.type), "v": p.volume, "po": p.price_open,
                "sl": p.sl, "tp": p.tp, "k": k, "sm": sm,
                "tr": 1 if p.ticket in tr else 0,
            }
        for o in ordenes:
            if int(o.type) in (2, 3, 4, 5):
                out["ord"][str(o.ticket)] = {
                    "s": o.symbol, "t": int(o.type), "v": o.volume_current, "po": o.price_open,
                    "sl": o.sl, "tp": o.tp, "k": k, "sm": sm,
                    "tt": int(o.type_time), "ex": int(o.time_expiration or 0),
                    "oco": 1 if o.ticket in oco_tks else 0,
                }
    except Exception:
        pass
    return out
