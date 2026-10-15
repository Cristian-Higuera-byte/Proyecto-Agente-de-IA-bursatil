"""Consultas de la cuenta: resumen, posiciones abiertas, órdenes pendientes e historial de operaciones."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fuentes.mt5_fuentes.conexion import _sesion
from fuentes.mt5_fuentes.errores import ErrorMT5
from fuentes.mt5_fuentes.utiles import _como_tupla, _hora_utc, _nivel, _num, _resolver


def cuenta() -> dict[str, Any]:
    with _sesion() as mt5:
        c = mt5.account_info()
        if c is None:
            raise ErrorMT5("No hay una cuenta iniciada en MT5.")
        return {
            "fuente": "MetaTrader 5",
            "tipo": "DEMO" if getattr(c, "trade_mode", 0) == 0 else "REAL",
            "moneda": getattr(c, "currency", "USD"),
            "balance": _num(getattr(c, "balance", None), 2),
            "equidad": _num(getattr(c, "equity", None), 2),
            "beneficio_flotante": _num(getattr(c, "profit", None), 2),
            "margen_usado": _num(getattr(c, "margin", None), 2),
            "margen_libre": _num(getattr(c, "margin_free", None), 2),
            "nivel_margen_pct": _num(getattr(c, "margin_level", None), 2),
            "apalancamiento": getattr(c, "leverage", None),
            "consultado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }


def posiciones(simbolo: str | None = None) -> dict[str, Any]:
    with _sesion() as mt5:
        sym = _resolver(mt5, simbolo) if simbolo else None
        pos_tuple = mt5.positions_get(symbol=sym) if sym else mt5.positions_get()
        pos_tuple = _como_tupla(mt5, pos_tuple, "obtener posiciones")

        resultado = []
        for p in pos_tuple:
            resultado.append({
                "ticket": getattr(p, "ticket", None),
                "simbolo": getattr(p, "symbol", None),
                "tipo": "COMPRA" if getattr(p, "type", 0) == 0 else "VENTA",
                "lotes": _num(getattr(p, "volume", None)),
                "precio_apertura": _num(getattr(p, "price_open", None)),
                "precio_actual": _num(getattr(p, "price_current", None)),
                "sl": _nivel(getattr(p, "sl", None)),
                "tp": _nivel(getattr(p, "tp", None)),
                "beneficio": _num(getattr(p, "profit", None)),
                "swap": _num(getattr(p, "swap", None)),
            })

        return {
            "fuente": "MetaTrader 5",
            "total_posiciones": len(resultado),
            "posiciones": resultado,
            "consultado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }


def ordenes_pendientes(simbolo: str | None = None) -> dict[str, Any]:
    with _sesion() as mt5:
        sym = _resolver(mt5, simbolo) if simbolo else None
        ordenes = mt5.orders_get(symbol=sym) if sym else mt5.orders_get()
        ordenes = _como_tupla(mt5, ordenes, "obtener órdenes pendientes")

        resultado = []
        tipos_orden = {2: "BUY LIMIT", 3: "SELL LIMIT", 4: "BUY STOP", 5: "SELL STOP"}
        for o in ordenes:
            t = getattr(o, "type", -1)
            resultado.append({
                "ticket": getattr(o, "ticket", None),
                "simbolo": getattr(o, "symbol", None),
                "tipo": tipos_orden.get(t, f"TIPO_{t}"),
                "lotes": _num(getattr(o, "volume_initial", None)),
                "precio_orden": _num(getattr(o, "price_open", None)),
                "sl": _nivel(getattr(o, "sl", None)),
                "tp": _nivel(getattr(o, "tp", None)),
            })

        return {
            "fuente": "MetaTrader 5",
            "total_ordenes": len(resultado),
            "ordenes": resultado,
            "consultado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }


def historial_operaciones(dias: int = 30, simbolo: str | None = None, ultimas: int = 15) -> dict[str, Any]:
    with _sesion() as mt5:
        hasta = datetime.now(timezone.utc)
        desde = hasta - timedelta(days=max(1, dias))
        sym_filter = _resolver(mt5, simbolo) if simbolo else None

        deals = mt5.history_deals_get(desde, hasta)
        deals = _como_tupla(mt5, deals, "obtener historial de operaciones")

        operaciones = []
        lucro_total = 0.0
        ganadoras = 0
        perdedoras = 0

        for d in deals:
            entry = getattr(d, "entry", None)
            deal_sym = getattr(d, "symbol", None)
            if entry in (1, 2):
                if sym_filter and deal_sym != sym_filter:
                    continue

                profit = _num(getattr(d, "profit", 0.0)) or 0.0
                lucro_total += profit

                if profit > 0:
                    ganadoras += 1
                elif profit < 0:
                    perdedoras += 1

                operaciones.append({
                    "ticket": getattr(d, "ticket", None),
                    "simbolo": deal_sym,
                    "tipo": "COMPRA" if getattr(d, "type", 0) == 0 else "VENTA",
                    "lotes": _num(getattr(d, "volume", None)),
                    "precio": _num(getattr(d, "price", None)),
                    "beneficio": profit,
                    "fecha_utc": _hora_utc(getattr(d, "time", 0), mt5),
                })

        total_ops = ganadoras + perdedoras
        win_rate = (ganadoras / total_ops * 100) if total_ops > 0 else 0.0

        return {
            "fuente": "MetaTrader 5",
            "dias_consultados": dias,
            "resumen": {
                "total_operaciones": total_ops,
                "ganadoras": ganadoras,
                "perdedoras": perdedoras,
                "tasa_acierto_pct": round(win_rate, 2),
                "beneficio_neto_total": round(lucro_total, 2),
            },
            "ultimas_operaciones": operaciones[-ultimas:] if ultimas > 0 else [],
            "consultado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
