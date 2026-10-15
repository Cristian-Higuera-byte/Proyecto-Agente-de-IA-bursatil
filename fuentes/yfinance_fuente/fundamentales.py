"""Datos fundamentales (Ticker.info) y estados financieros."""
from __future__ import annotations

from typing import Any

import yfinance as yf  # type: ignore[import-untyped]

from fuentes.yfinance_fuente.cache import _cacheado
from fuentes.yfinance_fuente.constantes import _CAMPOS_NUM, _CAMPOS_TEXTO, _ESTADOS
from fuentes.yfinance_fuente.utiles import _num, _simbolo, _sin_nulos


def fundamentales(simbolo: str) -> dict[str, Any]:
    s = _simbolo(simbolo)

    def _fn() -> dict[str, Any]:
        info = yf.Ticker(s).info or {}
        if len(info) <= 1:
            raise ValueError(
                f"Yahoo no tiene datos fundamentales para '{s}'. Es normal en forex, "
                "índices y cripto; para acciones verifica el símbolo."
            )
        datos: dict[str, Any] = {"simbolo": s}
        for clave, campo in _CAMPOS_TEXTO.items():
            datos[clave] = info.get(campo)
        for clave, campo in _CAMPOS_NUM.items():
            datos[clave] = _num(info.get(campo))
        descripcion = info.get("longBusinessSummary")
        if descripcion:
            datos["descripcion"] = descripcion[:500] + ("..." if len(descripcion) > 500 else "")
        datos["nota"] = (
            "Márgenes, ROE, ROA y crecimientos vienen como fracción (0.25 = 25%). "
            "deuda_sobre_capital viene en porcentaje (150 = 150%)."
        )
        return _sin_nulos(datos)

    return _cacheado(f"fundamentales:{s}", 3600, _fn)


def estados_financieros(
    simbolo: str, tipo: str = "resultados", frecuencia: str = "anual", periodos: int = 4
) -> dict[str, Any]:
    s = _simbolo(simbolo)
    if tipo not in _ESTADOS:
        raise ValueError(f"Tipo inválido: {tipo!r}. Opciones: {', '.join(_ESTADOS)}")
    if frecuencia not in ("anual", "trimestral"):
        raise ValueError("frecuencia debe ser 'anual' o 'trimestral'.")
    n = max(1, min(int(periodos), 8))
    anual, trimestral, filas = _ESTADOS[tipo]
    atributo = anual if frecuencia == "anual" else trimestral

    def _fn() -> dict[str, Any]:
        df = getattr(yf.Ticker(s), atributo)
        if df is None or df.empty:
            raise ValueError(
                f"Sin estado de {tipo} ({frecuencia}) para '{s}'. Índices, forex y cripto no tienen estados financieros."
            )
        presentes = [f for f in filas if f in df.index]
        df = df.loc[presentes] if presentes else df.head(15)

        salida = []
        for columna in df.columns[:n]:  # Yahoo entrega primero el periodo más reciente
            fila: dict[str, Any] = {
                "periodo": columna.strftime("%Y-%m-%d") if hasattr(columna, "strftime") else str(columna)
            }
            for item, valor in df[columna].items():
                fila[str(item)] = _num(valor, 2)
            salida.append(fila)
        return {
            "simbolo": s,
            "tipo": tipo,
            "frecuencia": frecuencia,
            "periodos": salida,
            "nota": "Cifras en la moneda de reporte de la empresa.",
        }

    return _cacheado(f"estados:{s}:{tipo}:{frecuencia}:{n}", 6 * 3600, _fn)
