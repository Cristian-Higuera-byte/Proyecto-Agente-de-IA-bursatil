"""Diagnóstico y reparación del panel derecho (rail + Profundidad/DOM).

Ejecutar desde la RAÍZ del proyecto:   python Instaladores/reparar_panel_derecho.py

Comprueba y arregla, con copia .bak de lo que toque:
  1. Marcadores de conflicto de git (<<<<<<< / ======= / >>>>>>>) que hayan quedado en archivos .py.
  2. components/dom_panel.py: que al final de renderizar_panel_dom() se llame a _escalera()
     (si falta, el panel muestra el título «Profundidad» pero NO la escalera de precios).
  3. components/panel_rail.py: que se inyecte el script del rail (components.html(_JS, ...)),
     que alterna los paneles Operar/Profundidad al pulsar los iconos.
  4. Que los 4 archivos que tuvieron conflicto compilen.
"""
import os, py_compile, re, sys

RAIZ = os.getcwd()
if not os.path.isfile(os.path.join(RAIZ, "app.py")):
    sys.exit("Ejecuta este script desde la raíz del proyecto (donde está app.py).")


def leer(rel):
    ruta = os.path.join(RAIZ, *rel.split("/"))
    with open(ruta, "rb") as f:
        crudo = f.read()
    return ruta, crudo, ("\r\n" in crudo.decode("utf-8"))


def guardar(ruta, crudo, texto, crlf):
    with open(ruta + ".bak", "wb") as f:
        f.write(crudo)
    with open(ruta, "wb") as f:
        f.write((texto.replace("\n", "\r\n") if crlf else texto).encode("utf-8"))


def sin_conflictos(texto):
    salida, estado = [], 0
    for ln in texto.splitlines(keepends=True):
        s = ln.rstrip("\r\n")
        if s.startswith("<<<<<<<"): estado = 1; continue
        if s.startswith("=======") and estado == 1: estado = 2; continue
        if s.startswith(">>>>>>>") and estado == 2: estado = 0; continue
        if estado == 1: continue
        salida.append(ln)
    return None if estado else "".join(salida)


problemas, arreglos = 0, 0

# 1) marcadores de conflicto en cualquier .py del proyecto (sin entornos virtuales)
for base, dirs, archivos in os.walk(RAIZ):
    dirs[:] = [d for d in dirs if d not in ("envir", "env", "venv", ".venv", ".git", "__pycache__", ".back", "Instaladores", "node_modules")]
    for nombre in archivos:
        if not nombre.endswith(".py"):
            continue
        ruta = os.path.join(base, nombre)
        with open(ruta, "rb") as f:
            crudo = f.read()
        texto = crudo.decode("utf-8", errors="replace")
        if re.search(r"^(<<<<<<<|>>>>>>>)", texto, re.M):
            problemas += 1
            limpio = sin_conflictos(texto)
            rel = os.path.relpath(ruta, RAIZ)
            if limpio is None:
                print("  !!  marcadores incompletos, revisa a mano:", rel)
            else:
                crlf = "\r\n" in texto
                guardar(ruta, crudo, limpio.replace("\r\n", "\n"), crlf); arreglos += 1
                print("  OK  conflicto resuelto (se queda con «Stashed changes»):", rel)

# 2) dom_panel.py: la escalera
ruta, crudo, crlf = leer("components/dom_panel.py")
t = crudo.decode("utf-8").replace("\r\n", "\n")
if "def _escalera" not in t:
    problemas += 1
    print("  !!  dom_panel.py no define _escalera(): falta código del panel. Restaura el archivo desde git (git checkout -- components/dom_panel.py).")
elif not re.search(r"^[ ]{8}_escalera\(\)[ ]*$", t, re.M):
    problemas += 1
    t = t.rstrip("\n") + "\n\n        _escalera()\n"
    guardar(ruta, crudo, t, crlf); arreglos += 1
    print("  OK  dom_panel.py: faltaba la llamada _escalera() (por eso se veía el título sin la escalera). Añadida.")
else:
    print("  --  dom_panel.py: la llamada a _escalera() está.")

# 3) panel_rail.py: el script del rail
ruta, crudo, crlf = leer("components/panel_rail.py")
t = crudo.decode("utf-8").replace("\r\n", "\n")
if not re.search(r"components\.html\(_JS", t):
    problemas += 1
    t = t.rstrip("\n") + '\n\n    # Script que alterna los paneles sin reejecutar Python.\n    with st.container(key="pj_railjs"):\n        components.html(_JS, height=0)\n'
    guardar(ruta, crudo, t, crlf); arreglos += 1
    print("  OK  panel_rail.py: faltaba el script del rail (los iconos no abrían/cerraban los paneles). Añadido.")
else:
    print("  --  panel_rail.py: el script del rail está.")
for clave, msg in [("renderizar_panel_dom()", "no llama a renderizar_panel_dom()"), ('"dom"', "no define el botón «dom» en BOTONES")]:
    if clave not in t:
        problemas += 1
        print("  !!  panel_rail.py " + msg + ": restaura el archivo desde git (git checkout -- components/panel_rail.py).")

# 4) compilación
for rel in ["components/dom_panel.py", "components/panel_rail.py", "servidor_datos.py", "herramientas/__init__.py"]:
    try:
        py_compile.compile(os.path.join(RAIZ, *rel.split("/")), doraise=True)
        print("  OK  compila:", rel)
    except Exception as e:
        problemas += 1
        print("  !!  NO compila:", rel, "->", e)

print("\nResultado: %d problema(s) detectado(s), %d arreglado(s)." % (problemas, arreglos))
print("Reinicia Streamlit (Ctrl+C y vuelve a lanzarlo) y pulsa el icono ≡ del lateral derecho.")
