"""Tarjeta KPI del Resumen (icono, valor, pie y pastilla), con atributos data-pj-* para el feed en vivo."""
from componentes_plataforma.resumen.datos import ACC


def card(clave, k, valor, unidad="", foot="", pill_html="", arrow=False, valcls="rs-neu",
          val_attrs=""):
    """val_attrs: atributos data-pj-* para que el feed pinte el valor EN VIVO
    (sub-segundo, sin rerun) igual que el resto del dashboard."""
    acc, ico, icbg, icfg = ACC[clave]
    ar = ""
    if arrow:
        ar = ("<span class='rs-arrow'>▲</span>" if valcls == "rs-up"
              else "<span class='rs-arrow'>▼</span>" if valcls == "rs-down" else "")
    u = f"<span class='u'>{unidad}</span>" if unidad else ""
    foot_html = f"<div class='rs-foot'>{foot}</div>" if foot else ""
    return (
        f"<div class='rs-card' style='--acc:{acc};--icbg:{icbg};--icfg:{icfg}'>"
        f"<div class='rs-ctop'><div class='rs-k'>{k}</div>"
        f"<div class='rs-cico'><span class='m'>{ico}</span></div></div>"
        f"<div class='rs-v'><span class='{valcls}' {val_attrs}>{ar}{valor}</span>{u}{pill_html}</div>"
        f"{foot_html}</div>"
    )
