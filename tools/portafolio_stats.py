"""
portafolio_stats.py
-------------------
Agregador de estadísticas del portafolio para la vista "Resumen" (dashboard F).

Hace UNA lectura de la cuenta + posiciones abiertas + historial de operaciones de
MT5 y devuelve TODO calculado, para que la UI solo pinte. Todo sale de datos
reales de MT5 (no se inventan números):

  - Capital:                account_info (equity, balance, margen libre).
  - P&L diario / mensual:   realizado (cierres de history_deals por fecha) + flotante
                            (posiciones abiertas).
  - Comisiones y swaps:     campos `commission`/`fee`/`swap` de cada deal.
  - Exposición:             notional por activo (volumen x contract_size x precio) y
                            margen usado; largos vs cortos.
  - Riesgo:                 nivel de margen + pérdida máxima DEFINIDA (posiciones con
                            SL) y aviso de las que no tienen SL (riesgo indefinido).
  - Drawdown (balance):     reconstruido desde la curva de balance de los cierres.
  - Dividendos:             ajustes de dividendo (operaciones de balance de MT5).
  - Rentabilidad acumulada: equity frente al depósito inicial.
  - Serie de balance:       para dibujar la curva de equity/balance.

Limitaciones honestas (ver bitácora):
  - El drawdown de EQUITY real necesita registrar snapshots (MT5 no los guarda);
    aquí se entrega el de BALANCE, que solo cambia en cada cierre. El de equity se
    alimentará del log que escribe servidor_datos.py.
  - Los dividendos dependen de que el bróker genere el evento; en demo puede no
    haber ninguno, en cuyo caso `dividendos_total` = 0 y la UI lo indica.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from tools.mt5_bridge import (MT5_LOCK, inicializar_mt5, obtener_info_cuenta,
                              obtener_posiciones, resolver_simbolo)
from tools import watchlist_manager as wl
from tools import equity_store

try:
    import MetaTrader5 as mt5
except Exception:                      # pragma: no cover - MT5 solo en Windows con terminal
    mt5 = None


def _inicio_dia() -> float:
    """Epoch del inicio del día de hoy (hora local)."""
    hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return hoy.timestamp()


def _inicio_mes() -> float:
    hoy = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return hoy.timestamp()


def _neto_deal(d) -> float:
    """P/G neto de un deal: profit + swap + comisión + fee (igual que la Cartera)."""
    return (float(getattr(d, "profit", 0.0) or 0.0)
            + float(getattr(d, "swap", 0.0) or 0.0)
            + float(getattr(d, "commission", 0.0) or 0.0)
            + float(getattr(d, "fee", 0.0) or 0.0))


def _contract_size(symbol: str) -> float:
    """Tamaño de contrato del símbolo (para el notional de la exposición)."""
    if mt5 is None:
        return 0.0
    try:
        with MT5_LOCK:
            info = mt5.symbol_info(symbol)
        return float(getattr(info, "trade_contract_size", 0.0) or 0.0) if info else 0.0
    except Exception:
        return 0.0


def _valor_punto(symbol: str) -> tuple[float, float]:
    """(k, point): k = valor de 1 unidad de precio por lote en moneda de cuenta
    (tick_value/tick_size); point = tamaño del punto. Para el riesgo definido."""
    if mt5 is None:
        return 0.0, 0.0
    try:
        with MT5_LOCK:
            info = mt5.symbol_info(symbol)
        if not info:
            return 0.0, 0.0
        tv = float(getattr(info, "trade_tick_value", 0.0) or 0.0)
        ts = float(getattr(info, "trade_tick_size", 0.0) or 0.0)
        k = (tv / ts) if ts else 0.0
        return k, float(getattr(info, "point", 0.0) or 0.0)
    except Exception:
        return 0.0, 0.0


def _leer_deals(dias: int = 400):
    """Todos los deals del período (cierres + operaciones de balance). Se usa un
    rango amplio para reconstruir la curva de balance y el depósito inicial."""
    if mt5 is None:
        return []
    try:
        with MT5_LOCK:
            if not inicializar_mt5():
                return []
            deals = mt5.history_deals_get(datetime.now() - timedelta(days=dias),
                                          datetime.now() + timedelta(days=1))
        return list(deals or [])
    except Exception:
        return []


def calcular(dias_curva: int = 3650) -> dict:
    """Devuelve el diccionario completo de estadísticas del portafolio."""
    cuenta = obtener_info_cuenta()
    if "error" in cuenta:
        return {"error": cuenta["error"]}

    moneda = cuenta.get("currency", "USD")
    equity = float(cuenta.get("equity", 0.0) or 0.0)
    balance = float(cuenta.get("balance", 0.0) or 0.0)
    margen = float(cuenta.get("margin", 0.0) or 0.0)
    margen_libre = float(cuenta.get("margin_free", 0.0) or 0.0)
    margin_level = float(cuenta.get("margin_level", 0.0) or 0.0)

    posiciones = obtener_posiciones() or []
    deals = _leer_deals(dias_curva)

    ini_dia, ini_mes = _inicio_dia(), _inicio_mes()

    # ----- Realizado (cierres) por período + comisiones/swaps -----
    real_hoy = real_mes = real_total = 0.0
    com_hoy = com_mes = com_total = 0.0
    swap_hoy = swap_mes = swap_total = 0.0
    dividendos_total = 0.0
    dividendos_mes = 0.0
    n_dividendos = 0
    n_cierres_hoy = n_cierres_mes = 0

    DEAL_OUT = getattr(mt5, "DEAL_ENTRY_OUT", 1) if mt5 else 1
    TYPE_BALANCE = getattr(mt5, "DEAL_TYPE_BALANCE", 2) if mt5 else 2
    # MT5 tiene tipos de deal DEDICADOS para dividendos de CFDs de acciones; XM los
    # usa (no como balance genérico). Detectarlos por tipo es lo correcto; además se
    # mantiene el fallback por comentario en operaciones de balance (otros brókers).
    TIPOS_DIVIDENDO = {getattr(mt5, "DEAL_TYPE_DIVIDEND", 16) if mt5 else 16,
                       getattr(mt5, "DEAL_TYPE_DIVIDEND_FRANKED", 17) if mt5 else 17}

    curva = []   # (epoch, balance_acumulado) para la curva y el drawdown
    bal_acum = 0.0

    for d in sorted(deals, key=lambda x: getattr(x, "time", 0)):
        t = float(getattr(d, "time", 0) or 0)
        tipo = getattr(d, "type", None)
        entry = getattr(d, "entry", None)
        comentario = str(getattr(d, "comment", "") or "").lower()

        monto = float(getattr(d, "profit", 0.0) or 0.0)

        # Dividendos: tipos de deal dedicados de MT5 (lo que usa XM).
        if tipo in TIPOS_DIVIDENDO:
            dividendos_total += monto
            n_dividendos += 1
            if t >= ini_mes:
                dividendos_mes += monto
            bal_acum += monto
            curva.append((t, bal_acum))
            continue

        # Operaciones de BALANCE: depósitos/retiros y (en algunos brókers) dividendos.
        if tipo == TYPE_BALANCE:
            if "div" in comentario:          # fallback: dividendo marcado en el comentario
                dividendos_total += monto
                n_dividendos += 1
                if t >= ini_mes:
                    dividendos_mes += monto
            bal_acum += monto
            curva.append((t, bal_acum))
            continue

        # Cierres de posición: traen el P/G realizado.
        if entry != DEAL_OUT:
            continue
        neto = _neto_deal(d)
        com = float(getattr(d, "commission", 0.0) or 0.0) + float(getattr(d, "fee", 0.0) or 0.0)
        sw = float(getattr(d, "swap", 0.0) or 0.0)
        bal_acum += neto
        curva.append((t, bal_acum))

        real_total += neto; com_total += com; swap_total += sw
        if t >= ini_mes:
            real_mes += neto; com_mes += com; swap_mes += sw; n_cierres_mes += 1
        if t >= ini_dia:
            real_hoy += neto; com_hoy += com; swap_hoy += sw; n_cierres_hoy += 1

    # Depósito inicial = primera operación de balance (o el balance actual si no hay historial).
    deposito_inicial = next((float(getattr(d, "profit", 0.0) or 0.0)
                             for d in sorted(deals, key=lambda x: getattr(x, "time", 0))
                             if getattr(d, "type", None) == TYPE_BALANCE), 0.0)

    # ----- Flotante (posiciones abiertas) -----
    flotante = sum(float(p.get("profit", 0.0) or 0.0) + float(p.get("swap", 0.0) or 0.0)
                   for p in posiciones)

    # ----- Exposición por activo + largos/cortos -----
    exposicion = {}
    exp_largos = exp_cortos = 0.0
    for p in posiciones:
        sym = p["symbol"]
        vol = float(p.get("volumen", 0.0) or 0.0)
        precio = float(p.get("precio_actual", 0.0) or 0.0) or float(p.get("precio_apertura", 0.0) or 0.0)
        cs = _contract_size(resolver_simbolo(sym))
        notional = vol * cs * precio
        es_compra = p.get("tipo") == "Compra"
        if es_compra:
            exp_largos += notional
        else:
            exp_cortos += notional
        row = exposicion.setdefault(sym, {"nombre": wl.nombre_visible(sym), "notional": 0.0,
                                          "volumen": 0.0, "n": 0})
        row["notional"] += notional
        row["volumen"] += vol
        row["n"] += 1
    exposicion_lista = sorted(exposicion.values(), key=lambda r: r["notional"], reverse=True)
    exp_total = exp_largos + exp_cortos

    # ----- Riesgo: pérdida DEFINIDA (posiciones con SL) + sin SL -----
    riesgo_definido = 0.0
    sin_sl = 0
    for p in posiciones:
        sl = float(p.get("sl", 0.0) or 0.0)
        if sl <= 0:
            sin_sl += 1
            continue
        sym = resolver_simbolo(p["symbol"])
        k, _pt = _valor_punto(sym)
        ac = float(p.get("precio_actual", 0.0) or 0.0) or float(p.get("precio_apertura", 0.0) or 0.0)
        vol = float(p.get("volumen", 0.0) or 0.0)
        compra = p.get("tipo") == "Compra"
        # Pérdida si salta el SL desde el precio actual (solo si el SL está en contra).
        perdida = (ac - sl) if compra else (sl - ac)
        if k > 0 and perdida > 0:
            riesgo_definido += perdida * k * vol

    # Anclar la curva al balance ACTUAL: la reconstrucción acumula deltas desde 0,
    # pero si el depósito inicial quedó fuera de la ventana el origen estaría
    # desplazado (curva "falsa" en negativo). Se desplaza todo para que el último
    # punto coincida con el balance real; así la curva y el drawdown son correctos.
    if curva:
        offset = balance - curva[-1][1]
        curva = [(t, b + offset) for t, b in curva]

    # ----- Drawdown de balance (sobre la curva reconstruida) -----
    pico = -1e18
    dd_abs = 0.0
    dd_pct = 0.0
    for _t, b in curva:
        pico = max(pico, b)
        if pico > 0:
            caida = pico - b
            if caida > dd_abs:
                dd_abs = caida
                dd_pct = caida / pico * 100.0

    # ----- Drawdown de EQUITY real (snapshots de equity_store, Tanda 2) -----
    # Incluye el flotante de posiciones abiertas; MT5 no guarda esta serie, la va
    # registrando servidor_datos.py. Si aún no hay suficientes snapshots, la UI usa
    # el de balance y lo indica. Ver tools/equity_store.py (nota de escalado).
    eq_serie = equity_store.serie()
    dd_eq_abs = dd_eq_pct = 0.0
    eq_disponible = len(eq_serie) >= 3
    if eq_disponible:
        pico_e = -1e18
        for p in eq_serie:
            e = p[1]
            pico_e = max(pico_e, e)
            if pico_e > 0:
                caida = pico_e - e
                if caida > dd_eq_abs:
                    dd_eq_abs = caida
                    dd_eq_pct = caida / pico_e * 100.0

    # ----- Rentabilidad acumulada -----
    rent_abs = equity - deposito_inicial if deposito_inicial else 0.0
    rent_pct = (rent_abs / deposito_inicial * 100.0) if deposito_inicial else 0.0

    return {
        "moneda": moneda,
        "capital": {"equity": equity, "balance": balance,
                    "margen": margen, "margen_libre": margen_libre,
                    "margin_level": margin_level, "deposito_inicial": deposito_inicial},
        "pnl": {
            "dia": {"realizado": real_hoy, "flotante": flotante, "total": real_hoy + flotante,
                    "cierres": n_cierres_hoy},
            "mes": {"realizado": real_mes, "flotante": flotante, "total": real_mes + flotante,
                    "cierres": n_cierres_mes},
            "realizado_total": real_total,
            "flotante": flotante,
        },
        "comisiones": {"hoy": com_hoy, "mes": com_mes, "total": com_total,
                       "swap_hoy": swap_hoy, "swap_mes": swap_mes, "swap_total": swap_total},
        "exposicion": {"total": exp_total, "largos": exp_largos, "cortos": exp_cortos,
                       "por_activo": exposicion_lista, "n_posiciones": len(posiciones)},
        "riesgo": {"definido": riesgo_definido, "sin_sl": sin_sl,
                   "margin_level": margin_level, "margen_usado": margen},
        "drawdown": {"balance_abs": dd_abs, "balance_pct": dd_pct,
                     "equity_abs": dd_eq_abs, "equity_pct": dd_eq_pct,
                     "equity_disponible": eq_disponible, "equity_puntos": len(eq_serie)},
        "dividendos": {"total": dividendos_total, "mes": dividendos_mes, "n": n_dividendos},
        "rentabilidad": {"abs": rent_abs, "pct": rent_pct},
        "curva": curva,
    }
