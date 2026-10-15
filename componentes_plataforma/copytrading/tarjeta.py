"""Tarjeta de una estrategia en el listado (nombre, riesgo, sparkline, rentabilidad y métricas)."""
from componentes_plataforma.copytrading.datos import RIESGO_CLS, RIESGO_TXT
from componentes_plataforma.copytrading.graficos import avatar, spark


def tarjeta_html(e: dict) -> str:
    rcls = RIESGO_CLS[e["riesgo"]]
    return (
        "<div class='ct-card'>"
        "<div class='ct-head'>"
        f"<span class='ct-av'>{avatar(e['nombre'])}</span>"
        f"<div><div class='ct-nm'>{e['nombre']}</div><div class='ct-gs'>@{e['gestor']}</div></div>"
        f"<span class='ct-badge {rcls}'>{RIESGO_TXT[e['riesgo']]}</span>"
        "</div>"
        "<div class='ct-mid'>"
        f"{spark(e['id'])}"
        f"<div style='text-align:right;'><div class='ct-rent-lbl'>Rentabilidad 1 mes</div>"
        f"<div class='ct-rent'>{e['rent']:.2f}%</div></div>"
        "</div>"
        "<div class='ct-grid'>"
        f"<div><div class='k'>Fondos propios</div><div class='v'>${e['fondos']:,}</div></div>"
        f"<div><div class='k'>Invertido</div><div class='v'>${e['invertido']:,}</div></div>"
        f"<div><div class='k'>Inversión mín.</div><div class='v'>${e['inv_min']:,}</div></div>"
        f"<div><div class='k'>Comisión</div><div class='v'>{e['comision']}%</div></div>"
        f"<div><div class='k'>Inversores</div><div class='v'>{e['inversores']}</div></div>"
        f"<div><div class='k'>Drawdown</div><div class='v'>{e['drawdown']}%</div></div>"
        "</div></div>"
    )
