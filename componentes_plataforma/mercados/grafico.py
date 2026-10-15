"""Gráfico interactivo de la ficha (Lightweight Charts): carcasa HTML y JS en estatico/."""
import json
from pathlib import Path

import streamlit.components.v1 as components

from componentes_plataforma._estaticos import texto

_DIR = Path(__file__).parent / "estatico"


def _html_grafico() -> str:
    return texto(_DIR / "grafico_ficha.html").replace("__JS__", texto(_DIR / "grafico_ficha.js"))


def grafico(real: str, df_d1, df_h1, df_m5, dig: int, alto: int = 300):
    def _pts(df):
        if df is None or df.empty:
            return []
        return [{"time": int(ts.timestamp()), "value": round(float(v), dig)}
                for ts, v in df["close"].items()]
    data = {"d1": _pts(df_d1), "h1": _pts(df_h1), "m5": _pts(df_m5)}
    html = (_html_grafico().replace("__DATA__", json.dumps(data))
            .replace("__DIG__", str(dig)).replace("__H__", str(alto))
            .replace("__SYM__", json.dumps(real)))
    components.html(html, height=alto + 40)
