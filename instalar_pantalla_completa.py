"""Pantalla completa del gráfico: botones VENDER/COMPRAR a mercado y cambio de activo sin salir de pantalla completa.

USO: copia este archivo a la RAIZ del proyecto (donde esta app.py) y ejecutalo:
        python instalar_pantalla_completa.py
Despues REINICIA servidor_datos.py y Streamlit.

Que hace:
  1) Reemplaza/crea 8 archivos del gráfico en components/grafico/ (panel.py, ensamblador.py y los fragmentos de estatico/).
  2) En components/posiciones_grafico.py y servidor_datos.py agrega SOLO las lineas nuevas, buscando el punto exacto
     (no pisa el resto). Si no encuentra el punto de insercion NO modifica ningun archivo y te avisa.
Antes de escribir un archivo existente guarda una copia .bak.
"""
import base64
import io
import os
import shutil
import sys
import zipfile

ZIP_B64 = """
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
+Mf2u4v2sGik4bCJA5MSF5tqn7AcsoNkstieCKSwsArWHl0tSwPv9yW1XMCbfx6Dj5oFx/lyIdxSQeS//xDe9Cnqzv588keNp2kI
019vqoh5obHjO7YZx7exMHOolLlHviMc/nskyixsGl73fbBtYRUhJsOpclnsQvB26m1L8GXwj8/Z01dYnGChyveN/uaDe8vT1yXD
1U5Wm0roDSA+bMbU6YYHFsQcnYPeie7998dfdS5HoStbv5OX6GE1aoN66j6n7FmdbwxQVumVVinFiKrm49O9pvrZjYsi5dI08jvY
mXrujTXYCUp3yo/nvDUevGCPf0M29KT3r69UZmDtvZc7IHo+DPjyHNWsJQMMJVjYmXX08g8ygjWmEcAdAO4Cqe8GlMqAE/miEwLR
7U3ezMQ0Zd7ugG17L9UL/DGln/w+QgE1hD+y5NWv2ZpD+VMCFmJlQQf5nP9MwdBURQQ0PYq/UJRuoFxcllov34W5Qkmq3TGqzmm4
jLWS/Pf6kd1deHG3Hxot7cXFOERKbb2+2jBjYarTYnuq08Cq5VJAr3c4IPimrWYEB/uDiztewqPsE9XvVKK6hW6YPcdfl9ZU+AO+
H5Afjo7KK4PYAO1/UEsBAhQDFAAAAAgACahNXd/Qo7F0BAAA0goAABsAAAAAAAAAAAAAAIABAAAAAGNvbXBvbmVudHMvZ3JhZmlj
by9wYW5lbC5weVBLAQIUAxQAAAAIAAmoTV3PkKjLzAMAANUHAAAhAAAAAAAAAAAAAACAAa0EAABjb21wb25lbnRzL2dyYWZpY28v
ZW5zYW1ibGFkb3IucHlQSwECFAMUAAAACAAJqE1dcoGEZbYCAAAzBgAAKgAAAAAAAAAAAAAAgAG4CAAAY29tcG9uZW50cy9ncmFm
aWNvL2VzdGF0aWNvL2VzcXVlbGV0by5odG1sUEsBAhQDFAAAAAgACahNXelbc/gxAwAAYwgAADgAAAAAAAAAAAAAAIABtgsAAGNv
bXBvbmVudHMvZ3JhZmljby9lc3RhdGljby9jc3MvODBfcGFudGFsbGFfY29tcGxldGEuY3NzUEsBAhQDFAAAAAgACahNXSKhe9o3
AQAAKAMAAC8AAAAAAAAAAAAAAIABPQ8AAGNvbXBvbmVudHMvZ3JhZmljby9lc3RhdGljby9odG1sLzMwX2xpZW56by5odG1sUEsB
AhQDFAAAAAgACahNXU15wDyzAAAARQEAADgAAAAAAAAAAAAAAIABwRAAAGNvbXBvbmVudHMvZ3JhZmljby9lc3RhdGljby9odG1s
LzcwX3NlbGVjdG9yX2FjdGl2by5odG1sUEsBAhQDFAAAAAgACahNXR5QlCO8CAAAChsAADsAAAAAAAAAAAAAAIAByhEAAGNvbXBv
bmVudHMvZ3JhZmljby9lc3RhdGljby9qcy81MF90aWVtcG9fcmVhbF95X2FjY2lvbmVzLmpzUEsBAhQDFAAAAAgACahNXWrN/JM/
BgAAOBMAADYAAAAAAAAAAAAAAIAB3xoAAGNvbXBvbmVudHMvZ3JhZmljby9lc3RhdGljby9qcy81NV9wYW50YWxsYV9jb21wbGV0
YS5qc1BLBQYAAAAACAAIAOYCAAByIQAAAAA=
"""

# archivo -> [(texto_ancla, texto_nuevo, marca_de_ya_aplicado)]
PARCHES = {'components/posiciones_grafico.py': [("        '#pj-ed .nt{color:#8b949e;font-size:11.5px;text-align:center;padding:6px 16px 14px;}';", '        \'#pj-ed .nt{color:#8b949e;font-size:11.5px;text-align:center;padding:6px 16px 14px;}\' +\n        \'#pj-mercado{display:none;align-items:stretch;gap:0;margin:5px 0 3px;pointer-events:auto;border-radius:5px;overflow:hidden;\' +\n        \'box-shadow:0 2px 8px rgba(0,0,0,.45);font-family:"Source Sans Pro",system-ui,sans-serif;width:max-content;}\' +\n        \'#tv-wrap.pj-fs #pj-mercado{display:flex;}\' +\n        \'#pj-mercado button{display:flex;flex-direction:column;align-items:center;justify-content:center;min-width:92px;padding:5px 12px 4px;\' +\n        \'border:none;color:#fff;cursor:pointer;line-height:1.1;}\' +\n        \'#pj-mercado button b{font:700 14px ui-monospace,Consolas,monospace;}\' +\n        \'#pj-mercado button span{font:700 10px "Source Sans Pro",system-ui,sans-serif;letter-spacing:.4px;margin-top:2px;}\' +\n        \'#pj-mercado .vend{background:#e5484d;}#pj-mercado .vend:hover{background:#f2575c;}\' +\n        \'#pj-mercado .comp{background:#1fa463;}#pj-mercado .comp:hover{background:#27b872;}\' +\n        \'#pj-mercado .spr{display:flex;align-items:center;justify-content:center;min-width:34px;padding:0 6px;background:#0d1117;\' +\n        \'color:#c9d1d9;font:600 12px ui-monospace,Consolas,monospace;text-shadow:none;}\';', '#pj-mercado{display:none'), ('      // ---------- Menú del clic derecho ----------\n', '      // ---------- Botones VENDER / COMPRAR a mercado (solo en pantalla completa) ----------\n      // Misma lógica que el ticket: One-Click Trading activo -> al instante; apagado -> se confirma en el propio gráfico.\n      // Volumen = el del ticket (o el mínimo del símbolo si el ticket no está a la vista). Ejecuta por POST /mercado.\n      var mercado = document.createElement(\'div\'); mercado.id = \'pj-mercado\';\n      mercado.innerHTML = \'<button class="vend" type="button" title="Vender a mercado"><b>—</b><span>VENDER</span></button>\' +\n        \'<span class="spr" title="Spread">—</span>\' +\n        \'<button class="comp" type="button" title="Comprar a mercado"><b>—</b><span>COMPRAR</span></button>\';\n      var legendEl = document.getElementById(\'tv-legend\');\n      if (legendEl) legendEl.insertBefore(mercado, document.getElementById(\'tv-cmp-legend\'));\n      var mBid = mercado.querySelector(\'.vend b\'), mAsk = mercado.querySelector(\'.comp b\'), mSpr = mercado.querySelector(\'.spr\');\n      function actualizarMercado(){\n        txt(mBid, BID ? fmt(BID, DIGITS) : \'—\');\n        txt(mAsk, ASK ? fmt(ASK, DIGITS) : \'—\');\n        var sp = (BID && ASK) ? (ASK - BID) / (PIP > 0 ? PIP : Math.pow(10, -DIGITS)) : null;\n        txt(mSpr, sp === null ? \'—\' : sp.toFixed(1));\n      }\n      function ordenMercado(lado){\n        if (!BID || !ASK){ avisar(\'Sin precio en vivo: no se puede operar ahora\', true); return; }\n        var vol = volumenTicket(), compra = lado === \'BUY\', precio = compra ? ASK : BID;\n        accion(compra ? \'Comprar a mercado\' : \'Vender a mercado\',\n               \'<b>\' + (compra ? \'Compra\' : \'Venta\') + \' \' + fmt(vol, 2) + \'</b> \' + REAL +\n               \' al precio de mercado (~<b>\' + fmt(precio, DIGITS) + \'</b>)\', function(){\n          post(\'/mercado\', {symbol: REAL, lado: lado, volumen: vol}).then(function(res){\n            if (res.error){ avisar(res.error, true); return; }\n            avisar((compra ? \'Comprados \' : \'Vendidos \') + fmt(res.volume || vol, 2) + \' lote(s) de \' + REAL +\n                   \' a \' + fmt(res.price || precio, DIGITS), false);\n          });\n        });\n      }\n      mercado.addEventListener(\'mousedown\', function(e){ e.stopPropagation(); });\n      mercado.querySelector(\'.vend\').onclick = function(){ ordenMercado(\'SELL\'); };\n      mercado.querySelector(\'.comp\').onclick = function(){ ordenMercado(\'BUY\'); };\n\n      // ---------- Menú del clic derecho ----------\n', 'var mercado = document.createElement'), ('        var w = containerEl.clientWidth, h = containerEl.clientHeight;\n        capa.style.left', '        var w = containerEl.clientWidth, h = containerEl.clientHeight;\n        actualizarMercado();\n        capa.style.left', '        actualizarMercado();\n        capa.style.left'), ('      var V_API = 5;', '      var V_API = 6;', 'var V_API = 6;'), ('            if st.button("cerrar", key=f"chcls_{tk}"):\n                st.session_state.ca_cerrar = {\n                    "ticket": tk, "symbol": (p.get("symbol") or "").replace("...", ""),\n                    "profit": _neto(p), "tipo": p.get("tipo"), "volumen": p.get("volumen", 0),\n                }\n                st.session_state.pop("ca_result", None)\n                st.rerun(scope="app")', '            if st.button("cerrar", key=f"chcls_{tk}"):\n                st.session_state.ca_cerrar = {\n                    "ticket": tk, "symbol": (p.get("symbol") or "").replace("...", ""),\n                    "profit": _neto(p), "tipo": p.get("tipo"), "volumen": p.get("volumen", 0),\n                }\n                st.session_state.pop("ca_result", None)\n                st.rerun(scope="app")\n        # Cambio de activo desde el gráfico en pantalla completa: la lista que muestra el gráfico (watchlist) la deja\n        # components/grafico/panel.py en la sesión; el botón nº i la pulsa el JS del gráfico (selector de activo).\n        for i, ticker in enumerate(st.session_state.get("_grafico_lista_activos", [])):\n            if st.button("activo", key=f"chcls_sel_{i}"):\n                st.session_state.activo_seleccionado = ticker\n                st.rerun(scope="app")', 'chcls_sel_')], 'servidor_datos.py': [('                              eliminar_orden)\nfrom tools import', '                              eliminar_orden, ejecutar_orden_mercado)\nfrom tools import', 'eliminar_orden, ejecutar_orden_mercado)'), ('# 5 = OCO (One-Cancels-the-Other): motor que cancela la pata sobrante + flag "oco" por orden.\nVERSION_API = 5', '# 5 = OCO (One-Cancels-the-Other): motor que cancela la pata sobrante + flag "oco" por orden.\n# 6 = POST /mercado (orden a mercado desde los botones VENDER/COMPRAR del gráfico en pantalla completa).\nVERSION_API = 6', 'VERSION_API = 6'), ('                elif ruta == "orden/eliminar":\n                    res = eliminar_orden(int(datos["ticket"]))\n', '                elif ruta == "orden/eliminar":\n                    res = eliminar_orden(int(datos["ticket"]))\n                elif ruta == "mercado":\n                    lado = str(datos.get("lado", "")).upper()\n                    vol = float(datos["volumen"])\n                    if lado not in ("BUY", "SELL") or not vol > 0:\n                        res = {"error": "Orden a mercado no válida (lado o volumen)"}\n                    else:\n                        res = ejecutar_orden_mercado(str(datos["symbol"]), lado, vol)\n', 'elif ruta == "mercado":'), ('    POST /orden/eliminar  {"ticket"}   -> cancela una orden pendiente\n', '    POST /orden/eliminar  {"ticket"}   -> cancela una orden pendiente\n    POST /mercado {"symbol", "lado", "volumen"} -> orden a mercado (botones VENDER/COMPRAR del gráfico a pantalla completa)\n', 'POST /mercado {"symbol"')]}


def leer(ruta):
    with open(ruta, "rb") as f:
        crudo = f.read()
    crlf = b"\r\n" in crudo
    return crudo.decode("utf-8").replace("\r\n", "\n"), crlf


def escribir(ruta, texto, crlf):
    shutil.copy2(ruta, ruta + ".bak")
    if crlf:
        texto = texto.replace("\n", "\r\n")
    with open(ruta, "wb") as f:
        f.write(texto.encode("utf-8"))


def parchar(ruta, cambios):
    """Calcula el archivo parchado EN MEMORIA (no escribe). Devuelve (estado, detalle, texto_nuevo, crlf)."""
    if not os.path.isfile(ruta):
        return "FALTA", "no existe el archivo", None, False
    texto, crlf = leer(ruta)
    pendientes = []
    for ancla, nuevo, marca in cambios:
        if marca in texto:
            continue                       # ya estaba aplicado
        n = texto.count(ancla)
        if n != 1:
            return "ERROR", f"no encontre un punto de insercion unico (aparece {n} veces): {ancla.strip().splitlines()[0][:70]!r}", None, crlf
        pendientes.append((ancla, nuevo))
    if not pendientes:
        return "YA", "ya tenia los cambios de este ajuste", None, crlf
    for ancla, nuevo in pendientes:
        texto = texto.replace(ancla, nuevo, 1)
    return "OK", f"{len(pendientes)} cambio(s) por agregar", texto, crlf


def main():
    if not os.path.isfile("app.py") or not os.path.isdir(os.path.join("components", "grafico")):
        sys.exit("Ejecuta este archivo desde la RAIZ del proyecto (donde estan app.py y components/grafico).")
    print("== Archivos con cambios puntuales ==")
    plan = {}
    for ruta, cambios in PARCHES.items():
        estado, detalle, texto, crlf = parchar(ruta.replace("/", os.sep), cambios)
        plan[ruta] = (estado, texto, crlf)
        print(f"  [{estado:5}] {ruta}: {detalle}")
    if any(e in ("ERROR", "FALTA") for e, _, _ in plan.values()):
        print("\nNo se modifico NINGUN archivo (para no dejar el proyecto a medias).")
        print("Mandame el archivo que fallo y lo ajusto.")
        sys.exit(1)
    for ruta, (estado, texto, crlf) in plan.items():
        if estado == "OK":
            escribir(ruta.replace("/", os.sep), texto, crlf)
    print("== Archivos del gráfico ==")
    z = zipfile.ZipFile(io.BytesIO(base64.b64decode("".join(ZIP_B64.split()))))
    for nombre in z.namelist():
        destino = nombre.replace("/", os.sep)
        os.makedirs(os.path.dirname(destino) or ".", exist_ok=True)
        datos = z.read(nombre)
        if os.path.exists(destino):
            with open(destino, "rb") as f:
                if f.read() == datos:
                    print("  igual:", nombre)
                    continue
            shutil.copy2(destino, destino + ".bak")
        with open(destino, "wb") as f:
            f.write(datos)
        print("  copiado:", nombre)
    print("\nListo. Reinicia servidor_datos.py y Streamlit.")


if __name__ == "__main__":
    main()
