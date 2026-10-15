"""Búsqueda de símbolos, cotización e histórico de precios."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import yfinance as yf  # type: ignore[import-untyped]

from fuentes.yfinance_fuente.cache import _cacheado
from fuentes.yfinance_fuente.constantes import AVISO_RETRASO, INTERVALOS, PERIODOS
from fuentes.yfinance_fuente.utiles import _entero, _fmt_fecha, _leer, _num, _simbolo, _sin_nulos, _validar_fecha


# ──────────────────────────────────────────────────────────────
# Búsqueda de símbolos
# ──────────────────────────────────────────────────────────────
def buscar(consulta: str, max_resultados: int = 8) -> list[dict[str, Any]]:
    consulta = (consulta or "").strip()
    if not consulta:
        raise ValueError("Falta el texto a buscar.")
    n = max(1, min(int(max_resultados), 15))

    def _fn() -> list[dict[str, Any]]:
        resultado = yf.Search(consulta, max_results=n)
        return [
            _sin_nulos(
                {
                    "simbolo": q.get("symbol"),
                    "nombre": q.get("longname") or q.get("shortname"),
                    "tipo": q.get("quoteType"),
                    "bolsa": q.get("exchDisp") or q.get("exchange"),
                }
            )
            for q in (resultado.quotes or [])
        ]

    return _cacheado(f"buscar:{consulta.lower()}:{n}", 3600, _fn)


# ──────────────────────────────────────────────────────────────
# Cotización actual
# ──────────────────────────────────────────────────────────────
def cotizacion(simbolo: str) -> dict[str, Any]:
    s = _simbolo(simbolo)

    def _fn() -> dict[str, Any]:
        fi = yf.Ticker(s).fast_info
        precio = _leer(fi, "last_price")
        if precio is None:
            raise ValueError(
                f"Yahoo no devolvió precio para '{s}'. Verifica el símbolo "
                "(ej. AAPL, EURUSD=X, ^GSPC, BTC-USD, GC=F) o reintenta en un momento."
            )
        previo = _leer(fi, "previous_close")
        variacion = variacion_pct = None
        if previo:
            variacion = _num(precio - previo)
            variacion_pct = _num((precio / previo - 1) * 100, 2)

        return _sin_nulos(
            {
                "simbolo": s,
                "precio": precio,
                "cierre_anterior": previo,
                "variacion": variacion,
                "variacion_pct": variacion_pct,
                "apertura": _leer(fi, "open"),
                "maximo_dia": _leer(fi, "day_high"),
                "minimo_dia": _leer(fi, "day_low"),
                "volumen": _entero(_leer(fi, "last_volume")),
                "maximo_52s": _leer(fi, "year_high"),
                "minimo_52s": _leer(fi, "year_low"),
                "media_50d": _leer(fi, "fifty_day_average"),
                "media_200d": _leer(fi, "two_hundred_day_average"),
                "capitalizacion": _leer(fi, "market_cap"),
                "moneda": _leer(fi, "currency", texto=True),
                "bolsa": _leer(fi, "exchange", texto=True),
                "consultado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "aviso": AVISO_RETRASO,
            }
        )

    return _cacheado(f"cotizacion:{s}", 30, _fn)


# ──────────────────────────────────────────────────────────────
# Histórico de precios
# ──────────────────────────────────────────────────────────────
def historico(
    simbolo: str,
    periodo: str = "3mo",
    intervalo: str = "1d",
    inicio: str | None = None,
    fin: str | None = None,
    ultimas_velas: int = 20,
) -> dict[str, Any]:
    """Resumen estadístico de TODO el rango + las últimas N velas (para no inundar el contexto)."""
    s = _simbolo(simbolo)
    if intervalo not in INTERVALOS:
        raise ValueError(f"Intervalo inválido: {intervalo!r}. Opciones: {', '.join(INTERVALOS)}")
    if inicio:
        _validar_fecha(inicio, "inicio")
        if fin:
            _validar_fecha(fin, "fin")
    elif periodo not in PERIODOS:
        raise ValueError(f"Periodo inválido: {periodo!r}. Opciones: {', '.join(PERIODOS)}")
    n = max(0, min(int(ultimas_velas), 200))
    intradia = intervalo[-1] in ("m", "h")  # 1m, 5m, 60m, 1h... (no '1mo', '3mo')

    def _fn() -> dict[str, Any]:
        ticker = yf.Ticker(s)
        if inicio:
            df = ticker.history(start=inicio, end=fin, interval=intervalo, auto_adjust=True)
        else:
            df = ticker.history(period=periodo, interval=intervalo, auto_adjust=True)
        if df is None or df.empty:
            raise ValueError(
                f"Yahoo no devolvió datos para '{s}' con esos parámetros. Revisa el símbolo; "
                "los intervalos intradía solo tienen datos recientes (1m: 7 días, resto: ~60 días)."
            )
        df = df.dropna(subset=["Close"])

        cierres = df["Close"]
        retornos = cierres.pct_change().dropna()
        primero, ultimo = cierres.iloc[0], cierres.iloc[-1]

        resumen = _sin_nulos(
            {
                "velas_totales": len(df),
                "desde": _fmt_fecha(df.index[0], intradia),
                "hasta": _fmt_fecha(df.index[-1], intradia),
                "cierre_inicial": _num(primero),
                "cierre_final": _num(ultimo),
                "variacion_pct": _num((ultimo / primero - 1) * 100, 2) if primero else None,
                "maximo": _num(df["High"].max()),
                "fecha_maximo": _fmt_fecha(df["High"].idxmax(), intradia),
                "minimo": _num(df["Low"].min()),
                "fecha_minimo": _fmt_fecha(df["Low"].idxmin(), intradia),
                "volumen_promedio": _entero(df["Volume"].mean()),
                "desv_estandar_retornos_por_vela_pct": _num(retornos.std() * 100, 3) if len(retornos) > 1 else None,
            }
        )
        velas = [
            {
                "fecha": _fmt_fecha(idx, intradia),
                "apertura": _num(fila["Open"]),
                "maximo": _num(fila["High"]),
                "minimo": _num(fila["Low"]),
                "cierre": _num(fila["Close"]),
                "volumen": _entero(fila["Volume"]),
            }
            for idx, fila in df.tail(n).iterrows()
        ]
        return {
            "simbolo": s,
            "intervalo": intervalo,
            "resumen_rango_completo": resumen,
            "ultimas_velas": velas,
            "aviso": AVISO_RETRASO,
        }

    ttl = 60 if intradia else 600
    return _cacheado(f"historico:{s}:{periodo}:{intervalo}:{inicio}:{fin}:{n}", ttl, _fn)
