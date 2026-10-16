"""
estadisticas_diario.py
----------------
Trading Journal (sección E) — Tanda A: registro AUTOMÁTICO de operaciones cerradas
y estadísticas de rendimiento, todo derivado de los deals reales de MT5.

MT5 guarda cada operación como "deals": al abrir (DEAL_ENTRY_IN) y al cerrar
(DEAL_ENTRY_OUT), ligados por `position_id`. `obtener_historial` del bridge solo
mira los OUT (trae el P/G realizado); aquí se **emparejan IN + OUT por posición**
para reconstruir cada operación completa: entrada, salida, horas, tamaño, resultado,
comisión y swap. Soporta cierres parciales (varios OUT): se agrega por posición.

Estadísticas (todas calculables desde las operaciones cerradas):
  - Win rate, nº de operaciones, P&L total.
  - Profit Factor  = ganancias brutas / |pérdidas brutas|.
  - R/R promedio (payoff) = ganancia media de las ganadoras / pérdida media de las perdedoras.
  - Expectancy  = (winrate × ganancia media) − (lossrate × |pérdida media|)  [$ por operación].
  - Max drawdown sobre la curva de equity de operaciones cerradas (realizado acumulado).

NOTA FUTURO: el R/R *planificado* real (vs el stop con que se abrió) exige registrar
el SL/TP al colocar la orden (Tanda C, almacen_diario por position_id). Aquí el "R/R
promedio" es el payoff ratio, que no necesita el stop. Campos del usuario
(estrategia, emoción) y captura del gráfico = Tanda B (almacen_diario + mini-gráfico).
"""
from __future__ import annotations

from datetime import datetime, timedelta

from herramientas.puente_mt5 import MT5_LOCK, inicializar_mt5
from herramientas import gestor_lista_activos as wl
from herramientas import almacen_diario

try:
    from proveedores.selector_mt5 import mt5
except Exception:                      # pragma: no cover
    mt5 = None


def _leer_deals(dias: int):
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


def operaciones(dias: int = 365, limite: int = 500) -> list:
    """Operaciones cerradas reconstruidas (IN+OUT por position_id). Más reciente
    primero. Cada una: pos_id, symbol, nombre, tipo, volumen, entrada, salida,
    hora_in, hora_out, neto, profit, comision, swap, duracion_s."""
    if mt5 is None:
        return []
    ENTRY_IN = getattr(mt5, "DEAL_ENTRY_IN", 0)
    ENTRY_OUT = getattr(mt5, "DEAL_ENTRY_OUT", 1)
    TYPE_BUY = getattr(mt5, "DEAL_TYPE_BUY", 0)

    porpos: dict = {}
    for d in _leer_deals(dias):
        pid = int(getattr(d, "position_id", 0) or 0)
        entry = getattr(d, "entry", None)
        if pid == 0 or entry not in (ENTRY_IN, ENTRY_OUT):
            continue
        r = porpos.setdefault(pid, {"in_vol": 0.0, "in_pv": 0.0, "out_vol": 0.0,
                                    "out_pv": 0.0, "t_in": None, "t_out": None,
                                    "neto": 0.0, "profit": 0.0, "com": 0.0, "swap": 0.0,
                                    "symbol": getattr(d, "symbol", ""), "tipo": None})
        vol = float(getattr(d, "volume", 0.0) or 0.0)
        precio = float(getattr(d, "price", 0.0) or 0.0)
        t = int(getattr(d, "time", 0) or 0)
        prof = float(getattr(d, "profit", 0.0) or 0.0)
        com = float(getattr(d, "commission", 0.0) or 0.0) + float(getattr(d, "fee", 0.0) or 0.0)
        sw = float(getattr(d, "swap", 0.0) or 0.0)
        r["neto"] += prof + com + sw
        r["profit"] += prof
        r["com"] += com
        r["swap"] += sw
        if entry == ENTRY_IN:
            r["in_vol"] += vol
            r["in_pv"] += vol * precio
            r["t_in"] = t if r["t_in"] is None else min(r["t_in"], t)
            if r["tipo"] is None:
                r["tipo"] = "Compra" if getattr(d, "type", TYPE_BUY) == TYPE_BUY else "Venta"
        else:
            r["out_vol"] += vol
            r["out_pv"] += vol * precio
            r["t_out"] = t if r["t_out"] is None else max(r["t_out"], t)

    notas = almacen_diario.leer()           # notas del usuario + plan por position_id (B/C)
    salida = []
    for pid, r in porpos.items():
        if r["t_out"] is None or r["in_vol"] <= 0:
            continue                       # posición aún abierta (sin cierre) → no es del diario
        entrada = r["in_pv"] / r["in_vol"] if r["in_vol"] else 0.0
        salida_p = r["out_pv"] / r["out_vol"] if r["out_vol"] else 0.0
        sym = r["symbol"]
        compra = (r["tipo"] == "Compra")

        info = notas.get(str(pid), {})
        plan = info.get("plan") or {}
        sl = float(plan.get("sl", 0.0) or 0.0)
        tp = float(plan.get("tp", 0.0) or 0.0)
        ent_plan = float(plan.get("entrada", 0.0) or 0.0) or entrada
        rr_plan = rr_real = None
        if sl > 0:
            riesgo = (ent_plan - sl) if compra else (sl - ent_plan)   # distancia al stop
            if riesgo > 0:
                if tp > 0:
                    recompensa = (tp - ent_plan) if compra else (ent_plan - tp)
                    rr_plan = recompensa / riesgo                     # reward:risk planificado
                mov = (salida_p - entrada) if compra else (entrada - salida_p)
                rr_real = mov / riesgo                                # R realizado (múltiplo de R)

        salida.append({
            "pos_id": pid, "symbol": sym, "nombre": wl.nombre_visible(sym),
            "tipo": r["tipo"] or "—", "volumen": r["in_vol"],
            "entrada": entrada, "salida": salida_p,
            "hora_in": r["t_in"] or 0, "hora_out": r["t_out"] or 0,
            "neto": r["neto"], "profit": r["profit"], "comision": r["com"], "swap": r["swap"],
            "duracion_s": max(0, (r["t_out"] or 0) - (r["t_in"] or 0)),
            "estrategia": info.get("estrategia", ""), "emocion": info.get("emocion", ""),
            "razon": info.get("razon", ""), "plan": plan,
            "sl": sl, "tp": tp, "rr_plan": rr_plan, "rr_real": rr_real,
        })
    salida.sort(key=lambda x: x["hora_out"], reverse=True)
    return salida[:limite]


def estadisticas(ops: list) -> dict:
    """Métricas del diario a partir de las operaciones cerradas."""
    n = len(ops)
    if n == 0:
        return {"n": 0, "win_rate": 0.0, "pnl": 0.0, "profit_factor": 0.0,
                "expectancy": 0.0, "rr_prom": 0.0, "avg_win": 0.0, "avg_loss": 0.0,
                "max_dd": 0.0, "ganadoras": 0, "perdedoras": 0}
    ganadoras = [o for o in ops if o["neto"] > 0]
    perdedoras = [o for o in ops if o["neto"] < 0]
    g_brutas = sum(o["neto"] for o in ganadoras)
    p_brutas = -sum(o["neto"] for o in perdedoras)          # positivo
    pnl = sum(o["neto"] for o in ops)
    nw, nl = len(ganadoras), len(perdedoras)
    win_rate = nw / n * 100.0
    avg_win = (g_brutas / nw) if nw else 0.0
    avg_loss = (p_brutas / nl) if nl else 0.0
    profit_factor = (g_brutas / p_brutas) if p_brutas > 0 else (float("inf") if g_brutas > 0 else 0.0)
    rr_prom = (avg_win / avg_loss) if avg_loss > 0 else (float("inf") if avg_win > 0 else 0.0)
    # Expectancy en $ por operación (incluye ganadoras y perdedoras).
    expectancy = pnl / n
    # Max drawdown sobre la curva de equity de operaciones cerradas (orden cronológico).
    acum = 0.0
    pico = 0.0
    max_dd = 0.0
    for o in sorted(ops, key=lambda x: x["hora_out"]):
        acum += o["neto"]
        pico = max(pico, acum)
        max_dd = max(max_dd, pico - acum)
    # R medio realizado (múltiplo de R) sobre las operaciones que tienen stop planificado.
    reales = [o["rr_real"] for o in ops if o.get("rr_real") is not None]
    r_medio = (sum(reales) / len(reales)) if reales else None
    return {"n": n, "win_rate": win_rate, "pnl": pnl, "profit_factor": profit_factor,
            "expectancy": expectancy, "rr_prom": rr_prom, "avg_win": avg_win,
            "avg_loss": avg_loss, "max_dd": max_dd, "ganadoras": nw, "perdedoras": nl,
            "r_medio": r_medio, "con_plan": len(reales)}


def calcular(dias: int = 365, limite: int = 500) -> dict:
    ops = operaciones(dias, limite)
    return {"operaciones": ops, "stats": estadisticas(ops)}
