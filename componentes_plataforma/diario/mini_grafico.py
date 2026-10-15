"""Mini-gráfico SVG de velas de una operación, con marcas de entrada/salida y SL/TP."""
from componentes_plataforma.diario.datos import AZ, DN, TX, UP


def mini_grafico_svg(velas, o):
    """Mini-gráfico de velas de la operación con marcas de entrada/salida y SL/TP,
    etiquetas tipo pill (sin pisarse) y la paleta P&J. Velas: [{t,o,h,l,c}]."""
    if len(velas) < 2:
        return ("<div class='jr-empty'>No hay velas para esta operación "
                "(histórico fuera de rango).</div>")
    niveles = [o["entrada"], o["salida"]]
    if o.get("sl"):
        niveles.append(o["sl"])
    if o.get("tp"):
        niveles.append(o["tp"])
    lo = min(min(v["l"] for v in velas), *niveles)
    hi = max(max(v["h"] for v in velas), *niveles)
    rng = (hi - lo) or 1.0
    W, H, pad = 1000, 270, 16
    padR = 120          # espacio a la derecha para las etiquetas pill
    n = len(velas)
    cw = (W - pad - padR) / n
    def Y(p): return H - pad - (H - 2 * pad) * (p - lo) / rng
    def X(i): return pad + cw * (i + 0.5)

    cuerpo = []
    for i, v in enumerate(velas):
        col = UP if v["c"] >= v["o"] else DN
        x = X(i)
        cuerpo.append(f"<line x1='{x:.1f}' y1='{Y(v['h']):.1f}' x2='{x:.1f}' "
                      f"y2='{Y(v['l']):.1f}' stroke='{col}' stroke-width='1'/>")
        y1, y2 = Y(v["o"]), Y(v["c"])
        yt, hgt = min(y1, y2), max(1.0, abs(y1 - y2))
        bw = max(1.8, cw * 0.62)
        cuerpo.append(f"<rect x='{x-bw/2:.1f}' y='{yt:.1f}' width='{bw:.1f}' "
                      f"height='{hgt:.1f}' rx='1' fill='{col}'/>")

    def idx(ts):
        return min(range(n), key=lambda i: abs(velas[i]["t"] - ts))

    # Niveles con etiqueta pill a la derecha; se reparten en Y para no pisarse.
    lines = []
    etiquetas = []   # (y_real, color, texto)
    lines.append((Y(o["entrada"]), AZ, f"Entrada {o['entrada']:,.5f}", False))
    lines.append((Y(o["salida"]), TX, f"Salida {o['salida']:,.5f}", False))
    if o.get("sl"):
        lines.append((Y(o["sl"]), DN, f"SL {o['sl']:,.5f}", True))
    if o.get("tp"):
        lines.append((Y(o["tp"]), UP, f"TP {o['tp']:,.5f}", True))

    svg = list(cuerpo)
    # Dibujar las líneas horizontales (hasta donde empiezan las pills).
    xL = W - padR
    for y, col, txt, dash in lines:
        d = "stroke-dasharray='5 4'" if dash else ""
        svg.append(f"<line x1='{pad}' y1='{y:.1f}' x2='{xL:.1f}' y2='{y:.1f}' "
                   f"stroke='{col}' stroke-width='1.3' {d} opacity='.85'/>")

    # Repartir las pills en Y (anti-solape): ordenar por y y separar >= 20px.
    pills = sorted([(y, col, txt) for (y, col, txt, _d) in lines], key=lambda t: t[0])
    PH = 19
    for i in range(1, len(pills)):
        if pills[i][0] - pills[i - 1][0] < PH:
            pills[i] = (pills[i - 1][0] + PH, pills[i][1], pills[i][2])
    for y, col, txt in pills:
        yy = max(PH / 2 + 2, min(H - PH / 2 - 2, y))
        w = 9 + len(txt) * 5.6
        svg.append(
            f"<rect x='{xL + 6:.1f}' y='{yy - PH/2:.1f}' width='{w:.1f}' height='{PH}' "
            f"rx='5' fill='{col}' fill-opacity='.16' stroke='{col}' stroke-opacity='.6'/>"
            f"<text x='{xL + 6 + w/2:.1f}' y='{yy + 3.5:.1f}' fill='{col}' font-size='10.5' "
            f"font-family='ui-monospace,Consolas,monospace' text-anchor='middle'>{txt}</text>")

    # Puntos de entrada/salida sobre las velas.
    ie, isx = idx(o["hora_in"]), idx(o["hora_out"])
    svg.append(f"<circle cx='{X(ie):.1f}' cy='{Y(o['entrada']):.1f}' r='5' fill='{AZ}' "
               f"stroke='#0b1017' stroke-width='1.5'/>")
    svg.append(f"<circle cx='{X(isx):.1f}' cy='{Y(o['salida']):.1f}' r='5' fill='{TX}' "
               f"stroke='#0b1017' stroke-width='1.5'/>")
    return (f"<div class='jr-chart'><svg viewBox='0 0 {W} {H}' width='100%' height='270' "
            f"style='width:100%;height:270px;display:block'>"
            + "".join(svg) + "</svg></div>")
