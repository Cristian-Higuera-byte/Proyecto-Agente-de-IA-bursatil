"""Funciones y constantes auxiliares de las herramientas (sin registrar nada)."""
from __future__ import annotations

import math


def _sma(valores: list[float], periodo: int) -> float | None:
    if len(valores) < periodo:
        return None
    return sum(valores[-periodo:]) / periodo


def _ema_serie(valores: list[float], periodo: int) -> list[float]:
    if len(valores) < periodo:
        return []
    k = 2 / (periodo + 1)
    ema_list = [sum(valores[:periodo]) / periodo]
    for v in valores[periodo:]:
        ema_list.append((v * k) + (ema_list[-1] * (1 - k)))
    return ema_list


def _rsi(cierres: list[float], periodo: int = 14) -> float | None:
    if len(cierres) <= periodo:
        return None
    gains, losses = [], []
    for i in range(1, len(cierres)):
        diff = cierres[i] - cierres[i - 1]
        gains.append(max(0.0, diff))
        losses.append(max(0.0, -diff))

    avg_gain = sum(gains[:periodo]) / periodo
    avg_loss = sum(losses[:periodo]) / periodo

    for i in range(periodo, len(gains)):
        avg_gain = (avg_gain * (periodo - 1) + gains[i]) / periodo
        avg_loss = (avg_loss * (periodo - 1) + losses[i]) / periodo

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 2)


def _atr(maximos: list[float], minimos: list[float], cierres: list[float], periodo: int = 14) -> float | None:
    if len(cierres) <= periodo:
        return None
    tr_list = []
    for i in range(1, len(cierres)):
        tr = max(
            maximos[i] - minimos[i],
            abs(maximos[i] - cierres[i - 1]),
            abs(minimos[i] - cierres[i - 1]),
        )
        tr_list.append(tr)

    atr = sum(tr_list[:periodo]) / periodo
    for i in range(periodo, len(tr_list)):
        atr = (atr * (periodo - 1) + tr_list[i]) / periodo
    return atr


def _macd(cierres: list[float], rapida: int = 12, lenta: int = 26, senal: int = 9) -> tuple[float | None, float | None, float | None]:
    if len(cierres) < lenta + senal:
        return None, None, None
    ema_rapida = _ema_serie(cierres, rapida)
    ema_lenta = _ema_serie(cierres, lenta)

    diff_len = len(ema_rapida) - len(ema_lenta)
    macd_line = [r - l for r, l in zip(ema_rapida[diff_len:], ema_lenta)]

    signal_line_list = _ema_serie(macd_line, senal)
    if not signal_line_list:
        return None, None, None

    macd_val = macd_line[-1]
    signal_val = signal_line_list[-1]
    hist_val = macd_val - signal_val
    return macd_val, signal_val, hist_val


def _bollinger(cierres: list[float], periodo: int = 20, desv: float = 2.0) -> tuple[float | None, float | None, float | None]:
    if len(cierres) < periodo:
        return None, None, None
    sub = cierres[-periodo:]
    sma = sum(sub) / periodo
    varianza = sum((x - sma) ** 2 for x in sub) / periodo
    std = math.sqrt(varianza)
    return sma + (desv * std), sma, sma - (desv * std)
