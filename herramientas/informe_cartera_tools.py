"""Informe integral de la cartera abierta.

NOMBRE DEL ARCHIVO: herramientas/informe_cartera_tools.py

Junta en una sola llamada lo que hoy el agente tendría que encadenar a mano: exposición actual,
riesgo, volatilidad, distancia al stop, correlaciones entre las posiciones abiertas, noticias de
alto impacto y escenarios de la cartera. Cada sección se calcula por separado: si una falla se
informa en `secciones_no_disponibles` y el resto sigue valiendo. Los importes salen del cálculo de
beneficios de MT5 (moneda de la cuenta); nada se inventa ni se estima con tablas fijas.
"""

from __future__ import annotations

from typing import Any

from fuentes import mt5_fuentes as mt5_fuente
from herramientas import analisis_tools, cuantitativo_tools, macro_eventos_tools
from herramientas.base import herramienta

MAX_SIMBOLOS_VOLATILIDAD = 8
UMBRAL_CORRELACION = 0.70       # |correlación| a partir de la cual dos posiciones "se mueven juntas"
UMBRAL_EXPOSICION_EQUIDAD_PCT = 3.0   # una divisa cuyo 1% mueve la equidad más que esto se avisa como exposición alta
NIVEL_MARGEN_MINIMO_PCT = 200   # por debajo se avisa de poco margen de seguridad

_DIVISAS_FX = {"USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD", "SEK", "NOK", "MXN", "ZAR", "CLP", "TRY", "PLN"}


def _par_fx(simbolo: str) -> tuple[str, str] | None:
    """('EUR', 'USD') si el símbolo es un par de divisas (admite sufijos del broker: EURUSD.r)."""
    s = "".join(c for c in simbolo.upper() if c.isalpha())[:6]
    if len(s) == 6 and s[:3] in _DIVISAS_FX and s[3:] in _DIVISAS_FX:
        return s[:3], s[3:]
    return None


def _signo(tipo: str) -> int:
    return 1 if str(tipo).upper() in ("COMPRA", "BUY") else -1


def _sensibilidad_1pct(pos: dict[str, Any]) -> float | None:
    """Lo que gana (+) o pierde (-) la posición, en dinero, si el precio sube 1%."""
    precio = pos.get("precio_actual")
    if not precio:
        return None
    sube = mt5_fuente.resultado_si_precio(pos["simbolo"], "COMPRA", pos["lotes"], precio, precio * 1.01)
    if sube is None:
        return None
    return round(sube * _signo(pos["tipo"]), 2)   # firmada: compra gana si sube, venta pierde


def _exposicion(posiciones: list[dict[str, Any]], equidad: float) -> dict[str, Any]:
    por_activo: dict[str, dict[str, Any]] = {}
    por_divisa: dict[str, float] = {}
    for p in posiciones:
        s = _sensibilidad_1pct(p)
        if s is None:
            continue
        a = por_activo.setdefault(p["simbolo"], {"lotes_compra": 0.0, "lotes_venta": 0.0, "sensibilidad_1pct_usd": 0.0})
        a["lotes_compra" if _signo(p["tipo"]) > 0 else "lotes_venta"] += p["lotes"]
        a["sensibilidad_1pct_usd"] = round(a["sensibilidad_1pct_usd"] + s, 2)
        par = _par_fx(p["simbolo"])
        if par:   # la posición larga en el par es larga en la base y corta en la cotizada
            por_divisa[par[0]] = por_divisa.get(par[0], 0.0) + s
            por_divisa[par[1]] = por_divisa.get(par[1], 0.0) - s
    for a in por_activo.values():
        a["lotes_compra"], a["lotes_venta"] = round(a["lotes_compra"], 2), round(a["lotes_venta"], 2)
        a["direccion_neta"] = (
            "LARGA" if a["sensibilidad_1pct_usd"] > 0 else "CORTA" if a["sensibilidad_1pct_usd"] < 0 else "NEUTRA"
        )
        a["sensibilidad_1pct_equidad_pct"] = round(a["sensibilidad_1pct_usd"] / equidad * 100, 2) if equidad else None
    divisas = {d: round(v, 2) for d, v in sorted(por_divisa.items(), key=lambda kv: -abs(kv[1]))}
    mayor = next(iter(divisas.items()), None)
    return {
        "por_activo": por_activo,
        "por_divisa_fx_usd_por_1pct": divisas,
        "nota": (
            "Sensibilidad = ganancia/pérdida en dinero si el precio se mueve 1%, calculada por MT5 "
            "(positiva = gana si sube). Por divisa solo cuentan los pares de divisas; oro, índices y "
            "cripto aparecen únicamente por activo."
        ),
        "_mayor_divisa": (mayor[0], round(abs(mayor[1]) / equidad * 100, 2)) if mayor and equidad else None,
    }


def _volatilidad(simbolos: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for s in simbolos[:MAX_SIMBOLOS_VOLATILIDAD]:
        try:
            ind = analisis_tools.calcular_indicadores_tecnicos(simbolo=s, timeframe="D1", cantidad=60)
        except Exception:  # noqa: BLE001 - un símbolo sin datos no tumba el informe
            continue
        atr = (ind.get("indicadores") or {}).get("atr_14") or {}
        if atr.get("valor_absoluto"):
            out[s] = {
                "atr_diario": atr["valor_absoluto"],
                "atr_diario_pct": atr.get("volatilidad_pct"),
                "precio_actual": ind.get("precio_actual"),
            }
    return out


def _correlaciones(posiciones: list[dict[str, Any]]) -> dict[str, Any]:
    simbolos = sorted({p["simbolo"] for p in posiciones})
    if len(simbolos) < 2:
        return {"mensaje": "Se necesitan al menos 2 activos distintos abiertos para medir correlaciones."}
    res = cuantitativo_tools.calcular_matriz_correlacion(",".join(simbolos), 90)
    if "error" in res:
        return res
    matriz = res["matriz_correlacion"]
    direccion: dict[str, int] = {}
    for p in posiciones:
        direccion[p["simbolo"]] = direccion.get(p["simbolo"], 0) + _signo(p["tipo"]) * p["lotes"]
    pares = []
    for i, a in enumerate(res["activos_analizados"]):
        for b in res["activos_analizados"][i + 1:]:
            c = matriz[a][b]
            if abs(c) < UMBRAL_CORRELACION:
                continue
            # correlación "efectiva": si una larga y otra corta se mueven juntas, se compensan
            efectiva = c * (1 if direccion.get(a, 0) * direccion.get(b, 0) > 0 else -1)
            pares.append({
                "activos": [a, b],
                "correlacion": c,
                "efecto_en_cartera": (
                    "SE REFUERZAN (riesgo concentrado en la misma apuesta)" if efectiva > 0
                    else "SE COMPENSAN (cobertura parcial)"
                ),
            })
    return {
        "dias_historicos": res["dias_historicos"],
        "matriz_correlacion": matriz,
        "pares_relevantes": pares,
        "criterio": f"Relevante = correlación absoluta de {UMBRAL_CORRELACION} o más (retornos diarios).",
    }


def _noticias(posiciones: list[dict[str, Any]]) -> dict[str, Any]:
    divisas: list[str] = []
    for p in posiciones:
        par = _par_fx(p["simbolo"])
        claves = list(par) if par else (["XAU"] if "XAU" in p["simbolo"].upper() or "GOLD" in p["simbolo"].upper() else [])
        for d in claves:
            if d not in divisas:
                divisas.append(d)
    evaluadas = divisas[:5] or ["ALL"]
    resultados = {d: macro_eventos_tools.evaluar_riesgo_noticias_proximas(d) for d in evaluadas}
    if all(not r.get("disponible") for r in resultados.values()):
        return {"disponible": False, "mensaje": next(iter(resultados.values())).get("mensaje")}
    titulares: list[dict[str, Any]] = []
    vistos: set[str] = set()
    for d, r in resultados.items():
        for t in r.get("titulares_alto_impacto", []):
            if t["titulo"] not in vistos:
                vistos.add(t["titulo"])
                titulares.append({"divisa": d, **t})
    return {
        "disponible": True,
        "divisas_evaluadas": evaluadas,
        "nivel_cautela_macro": "PRECAUCIÓN" if titulares else "SIN SEÑALES EN TITULARES",
        "titulares_alto_impacto": titulares[:8],
        "limitacion": "Basado en titulares de Investing.com; no es un calendario con horas exactas.",
    }


def _escenarios(posiciones: list[dict[str, Any]], vol: dict[str, Any], riesgo: dict[str, Any], equidad: float) -> dict[str, Any]:
    adverso = favorable = 0.0
    sin_dato = 0
    for p in posiciones:
        v = vol.get(p["simbolo"])
        if not v or not p.get("precio_actual"):
            sin_dato += 1
            continue
        mov = v["atr_diario"]
        s = _signo(p["tipo"])
        contra = p["precio_actual"] - s * mov     # precio se mueve 1 ATR en contra de la posición
        pro = p["precio_actual"] + s * mov
        r_c = mt5_fuente.resultado_si_precio(p["simbolo"], p["tipo"], p["lotes"], p["precio_actual"], contra)
        r_p = mt5_fuente.resultado_si_precio(p["simbolo"], p["tipo"], p["lotes"], p["precio_actual"], pro)
        if r_c is None or r_p is None:
            sin_dato += 1
            continue
        adverso += r_c
        favorable += r_p

    def fila(nombre: str, delta: float | None, nota: str) -> dict[str, Any]:
        return {
            "escenario": nombre, "resultado_usd": None if delta is None else round(delta, 2),
            "resultado_equidad_pct": None if delta is None or not equidad else round(delta / equidad * 100, 2),
            "equidad_resultante_usd": None if delta is None else round(equidad + delta, 2), "nota": nota,
        }

    tot = riesgo.get("riesgo_total_acumulado_usd")
    objetivo = sum((p.get("beneficio_estimado_usd") or 0) for p in riesgo.get("posiciones", []))
    filas = [
        fila("Todos los stops se activan", None if tot is None else -tot,
             "Peor caso con las protecciones actuales; las posiciones sin SL no están incluidas."),
        fila("Todos los objetivos (TP) se cumplen", objetivo or None, "Solo posiciones con TP definido."),
        fila("Movimiento de 1 ATR diario EN CONTRA de cada posición", adverso if sin_dato < len(posiciones) else None,
             "Día adverso típico para toda la cartera a la vez."),
        fila("Movimiento de 1 ATR diario A FAVOR de cada posición", favorable if sin_dato < len(posiciones) else None,
             "Día favorable típico."),
    ]
    return {
        "escenarios": filas,
        "aviso": "Escenarios de referencia calculados con el ATR y los niveles actuales; no son predicciones ni tienen probabilidad.",
        "posiciones_sin_datos_de_volatilidad": sin_dato,
    }


def _alertas(cuenta: dict[str, Any], riesgo: dict[str, Any], expo: dict[str, Any], corr: dict[str, Any], noticias: dict[str, Any]) -> list[str]:
    a: list[str] = []
    if riesgo.get("posiciones_sin_stop_loss"):
        a.append(f"{riesgo['posiciones_sin_stop_loss']} posición(es) SIN Stop Loss: riesgo ilimitado.")
    try:
        from core import ordenes
        tope = ordenes.LIMITES.riesgo_max_total_pct
        if (riesgo.get("riesgo_total_equidad_pct") or 0) > tope:
            a.append(f"El riesgo total ({riesgo['riesgo_total_equidad_pct']}% de la equidad) supera el límite del agente ({tope}%).")
    except Exception:  # noqa: BLE001
        pass
    mayor = expo.get("_mayor_divisa")
    if mayor and mayor[1] >= UMBRAL_EXPOSICION_EQUIDAD_PCT:
        a.append(f"Exposición alta a {mayor[0]}: un movimiento de 1% en esa divisa mueve tu equidad ~{mayor[1]}%.")
    for par in corr.get("pares_relevantes", []):
        if par["efecto_en_cartera"].startswith("SE REFUERZAN"):
            a.append(f"{par['activos'][0]} y {par['activos'][1]} se mueven juntos (corr. {par['correlacion']}): es casi la misma apuesta.")
    nivel = cuenta.get("nivel_margen_pct")
    if nivel and nivel < NIVEL_MARGEN_MINIMO_PCT:
        a.append(f"Nivel de margen bajo ({nivel}%).")
    if noticias.get("nivel_cautela_macro") == "PRECAUCIÓN":
        a.append("Hay titulares sobre eventos macro de alto impacto relacionados con tus activos.")
    return a


@herramienta(
    descripcion=(
        "Informe integral de la cartera abierta en una sola llamada: exposición actual (por activo y por "
        "divisa, en dinero), riesgo total y por posición, volatilidad (ATR diario), distancia al stop, "
        "correlaciones relevantes entre las posiciones, noticias macro de alto impacto y escenarios de la "
        "cartera, más una lista de alertas. Úsala cuando pregunten cómo está la cartera, el riesgo "
        "general o la exposición total."
    ),
    parametros={},
    nombre="informe_cartera",
)
def informe_cartera() -> dict[str, Any]:
    cuenta = mt5_fuente.cuenta()
    posiciones = mt5_fuente.posiciones().get("posiciones", [])
    equidad = cuenta.get("equidad") or 0.0
    if not posiciones:
        return {
            "fuente": "MetaTrader 5",
            "total_posiciones": 0,
            "cuenta": cuenta,
            "mensaje": "No hay posiciones abiertas: no hay exposición ni riesgo en la cartera.",
        }

    fallos: dict[str, str] = {}

    def seccion(nombre: str, fn: Any, defecto: Any) -> Any:
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 - una sección caída no invalida las demás
            fallos[nombre] = str(e)[:160]
            return defecto

    riesgo = seccion("riesgo", analisis_tools.analizar_riesgo_posicion, {})
    expo = seccion("exposicion", lambda: _exposicion(posiciones, equidad), {})
    vol = seccion("volatilidad", lambda: _volatilidad(sorted({p["simbolo"] for p in posiciones})), {})
    corr = seccion("correlaciones", lambda: _correlaciones(posiciones), {})
    noticias = seccion("noticias", lambda: _noticias(posiciones), {})
    esc = seccion("escenarios", lambda: _escenarios(posiciones, vol, riesgo, equidad), {})
    alertas = seccion("alertas", lambda: _alertas(cuenta, riesgo, expo, corr, noticias), [])
    expo.pop("_mayor_divisa", None)

    return {
        "fuente": "MetaTrader 5 + Investing.com (titulares)",
        "total_posiciones": len(posiciones),
        "cuenta": {k: cuenta.get(k) for k in ("tipo", "moneda", "balance", "equidad", "beneficio_flotante",
                                              "margen_usado", "margen_libre", "nivel_margen_pct")},
        "alertas": alertas,
        "exposicion": expo,
        "riesgo": {k: riesgo.get(k) for k in ("riesgo_total_acumulado_usd", "riesgo_total_equidad_pct",
                                              "posiciones_sin_stop_loss", "aviso", "posiciones")},
        "volatilidad": vol,
        "correlaciones": corr,
        "noticias": noticias,
        "escenarios": esc,
        "secciones_no_disponibles": fallos,
    }
