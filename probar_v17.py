"""Prueba TEMPORAL de V17 en el servidor con la herramienta real de reportes (se borra después de usarla).

Usa usuarios de prueba (v17_a, v17_b) que no existen en la plataforma y borra sus carpetas al terminar.
Uso (desde la carpeta del proyecto, en el servidor):  python probar_v17.py
"""
import contextvars
import csv
import io
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

sys.path.insert(0, os.getcwd())
from herramientas import archivos_privados as ap                                # noqa: E402
from herramientas_agente.tablas_herramientas import herramientas as tablas      # noqa: E402
from nucleo_agente import contexto                                              # noqa: E402
from nucleo_agente.turnos import imagenes                                       # noqa: E402


def como(usuario, f, *a, **k):
    """Ejecuta f como la consulta del agente de ese usuario."""
    def correr():
        contexto.fijar_usuario(usuario)
        return f(*a, **k)
    return contextvars.copy_context().run(correr)


def reporte(usuario, datos, formato):
    """Genera un reporte de datos personalizados."""
    return como(usuario, tablas.generar_tabla_reporte, tipo_reporte="datos_personalizados", formato=formato, datos_json=json.dumps(datos))


def linea(nombre, ok, detalle=""):
    """Imprime una comprobación."""
    print(("OK    " if ok else "FALLA ") + nombre + (f": {detalle}" if detalle else ""), flush=True)
    return ok


todo = []
try:
    r = reporte("v17_a", [{"S": "<script>alert(1)</script>", "N": "\"><img src=x onerror=alert(1)>"}], "html")
    todo.append(linea("1 HTML escapado", "<script" not in r["tabla_renderizada"] and "&lt;script&gt;" in r["tabla_renderizada"], r["tabla_renderizada"][:90]))
    r = reporte("v17_a", [{"D": "=cmd|' /C calc'!A0"}, {"D": "+1+1"}, {"D": "-12.5"}], "csv")
    filas = list(csv.reader(io.StringIO(Path(r["archivo_guardado"]).read_text(encoding="utf-8"))))
    todo.append(linea("2 CSV neutralizado", [f[0] for f in filas[1:]] == ["'=cmd|' /C calc'!A0", "'+1+1", "-12.5"], str([f[0] for f in filas[1:]])))
    ruta = Path(r["archivo_guardado"])
    modo = oct(ruta.parent.stat().st_mode & 0o777)
    todo.append(linea("3 carpeta privada 0700 y fuera de static", modo == "0o700" and "static" not in ruta.parts, f"{ruta.parent.parent.parent.name}/{ruta.parent.parent.name}/{ruta.parent.name} modo {modo}"))
    todo.append(linea("4 nombre aleatorio y sin URL publica", len(ruta.stem) == 22 and "url_descarga" not in r, ruta.name))
    # el archivo NO se sirve por la web: la ruta publica devuelve la pagina de Streamlit, no el CSV
    web = subprocess.run(["curl", "-s", "-m", "10", f"https://pyj.rmcabogados.cl/data/archivos_usuarios/v17_a/reportes/{ruta.name}"], capture_output=True, text=True).stdout[:60]
    todo.append(linea("5 no se sirve por la web", "Streamlit" in web or "<!DOCTYPE" in web.upper() or "<!--" in web, web.replace("\n", " ")))
    # descarga cruzada
    todo.append(linea("6 otro usuario no lo lee", ap.leer(ruta, "v17_b") is None and ap.leer(ruta, "v17_a") is not None))
    todo.append(linea("7 colector no entrega a otro usuario", imagenes.archivos_de_resultado(r, "v17_b") == [] and imagenes.archivos_de_resultado(r, "v17_a") != []))
    # rutas fuera del espacio y enlace simbolico real
    fuera = Path("/tmp/v17_fuera.png")
    fuera.write_bytes(b"x")
    enlace = ap.carpeta_de("v17_a", "graficos") / "enlace.png"
    os.symlink(fuera, enlace)
    cand = [str(fuera), "/etc/passwd", str(Path.home() / ".bashrc"), str(enlace), str(ap.carpeta_de("v17_a", "graficos") / ".." / ".." / ".." / ".." / ".." / ".." / "tmp" / "v17_fuera.png")]
    todo.append(linea("8 rutas fuera / enlace simbolico rechazados", all(imagenes.imagenes_de_resultado({"archivo_guardado": c}, "v17_a") == [] for c in cand)))
    fuera.unlink()
    # exportaciones simultaneas
    res, barrera = [], threading.Barrier(30)

    def exportar(i):
        """Una exportacion a la vez que las demas."""
        barrera.wait()
        res.append(reporte("v17_a", [{"m": f"x{i}"}], "csv"))

    hs = [threading.Thread(target=exportar, args=(i,)) for i in range(30)]
    [h.start() for h in hs]
    [h.join() for h in hs]
    rutas = {x["archivo_guardado"] for x in res}
    todo.append(linea("9 30 exportaciones simultaneas", len(rutas) == 30 and all(Path(p).exists() for p in rutas), f"{len(rutas)} archivos distintos"))
    # tipo y formato validados
    errs = [como("v17_a", tablas.generar_tabla_reporte, tipo_reporte=t, formato=f) for t, f in [("../../etc/passwd", "csv"), ("datos_personalizados", "../x.py")]]
    todo.append(linea("10 tipo y formato validados", all("error" in e for e in errs)))
finally:
    shutil.rmtree(ap.raiz() / "v17_a", ignore_errors=True)
    shutil.rmtree(ap.raiz() / "v17_b", ignore_errors=True)
    print("limpieza:", "carpetas de prueba borradas" if not (ap.raiz() / "v17_a").exists() else "NO SE BORRARON", flush=True)
print("RESULTADO:", "todo OK" if todo and all(todo) else "HAY FALLOS")
