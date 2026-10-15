"""Arreglo: las vigilancias que prepara el agente se guardaban con el usuario 'local' y no aparecían en «Órdenes propuestas» (nucleo_agente/contexto.py).

Ejecutar desde la raíz del proyecto:   python instalar_arreglo_vigilancia_usuario.py
Idempotente, sin .bak. No instala nada si algún archivo difiere de la versión esperada.
"""
import base64, hashlib, io, json, os, sys, zipfile

PRE = {'nucleo_agente/contexto.py': 'a0b27e756a7a90b757825d7949ddef7b6cf6bc62815a3241acbac234913ea147'}
ARCHIVOS = ["nucleo_agente/contexto.py"]
ZIP_B64 = "UEsDBBQAAAAIAFWmT11d8l37eAQAACUMAAAZAAAAbnVjbGVvX2FnZW50ZS9jb250ZXh0by5wee1WTW/bRhC981cM5IsEyPQhKAooSFHXdlAFjm1YdYoiCJQRuaLXIHfl/ZCj/I38ghyDIofCx96iP9Y3FClFjhMEKGD0UB1skrs78+a9N0Pu0EgHbel3NaEDpzi3NLOOzvTyL6YFPWPH9Jtj4/E0KI9HI+XmOtPW03HIOU126FA7lWV6eWsG9Mz65Qf85eu4/GjozGkVLO388OjHR7SLvSM29FwXUZW0KzdBc2FxeXCpS4X1zJrAWbDpTBteXCH9z0XFukwzW2H5MoSZH+zt3dzcbHakWYmlFfo+UtrCcSWVLADNK1RyT1U48e26EuzYfZjf92Wi4cnwYHi6rY3wpd6A4vTsj+8J8oBFJZ1O56CFlysqa7Q+loFJGcqi85a611EvPxhZvORM9cD7yenzX86P6PDomPbPD34dvjgdkIlZqeyYC4V4e23R6WyRJMfs6VI5SK6xiJsc3lptJG8NTaOBqgYaG+sqLmuxjSV4Vk+Ag0uKPrJDE8BjltgVscJpm8Ko+O/YJ9vpQ3TG+j04VhCQulJZRE3RbBfoI8mWPk31FVPdEKTWyR6j5DvAryNIsolRmfI6oFG6sxTRU8pgbVfHn+tCl4yCEDAGWy3fB51xD8eoVEIqCm4SjNFGkctuL6UjX9tf0CTdRpIX7Hp9Yg9QkrcFLvS1EXCtfdCgQrgjr6hSbzOkT0XaJJk6W9F4PI0gRI3HpCtpJmJjbGAMFeOTpHk2ibpEJN/eNwrO2Xnps4tGgK+5BBfKQ0+pYK3+Y+qUNuOyg01s0OKGcy0MCuHL2w17CGdL7smoOgaFyMSTUkk9BdLmTIGrSe1C5HndQn1NM2kwIUe9AQ9MFyf7JJFqMmfOQiY7oFGAOlWpA80x1eaKuCGCHRJGQ9XyNo9A1aCELdhll3qOJ5K3LhNEZ2gGCQw7VTOxDYy5klC/hfpwDlIuFGZjrbLAWL4vMAOJJ1ohXY8WfWT0GnFzYXGG2NIMawBiIxYAiCSLLRV9iS7c1tXWdt0YFd0izbkxauNTMRzS4SZnt/zIK/O1IdfeYf9lgLmSA0CKSp1ay9gttwy+1mdSW4JscFYYXcOCJxkaqUyCgcRPfy7fuVxJq0uBEZZh/+lvCD++GF3snw8xSD4zXrrphJc+uFf0hAoF4wbXbT3Qp854djVuHTducnf6dIKJ0iPIdX/AbkL4ddpW1DmO5GrKsPWTptxe0mZJ78sBNC1qoh0Ki5kakC4ww9RLwbiLcNqo/BVeVLisVXPt4e4m8YBQW492f6ohD1a4Op2nd0T+VueVm7fMypAY0hLmvJ6gsq7z2mjr0QYPziG1gh0gjiVbJxdFo+dW75RGFjbiKTzN4vat7hZj1VkAqyzxPqftySWt0hgWPoDRlJuiDepJtj3NxDd+PdPSloH6f0tx6lXogqjPiBNxW6l6Dcl3R6vQilNrVg9VMwO+4KTWRz5DpAPvfxO2bQDyVtN2NcaMNkU0tpe2mJ2SF9AGOkzb7f33PlfwwfJ0ePLvvlYe9HNl5/9P4a/U9Q9QSwECFAMUAAAACABVpk9dXfJd+3gEAAAlDAAAGQAAAAAAAAAAAAAAgAEAAAAAbnVjbGVvX2FnZW50ZS9jb250ZXh0by5weVBLBQYAAAAAAQABAEcAAACvBAAAAAA="


def norm(b):
    return b.replace(b"\r\n", b"\n")


def main():
    z = zipfile.ZipFile(io.BytesIO(base64.b64decode(ZIP_B64)))
    nuevos = {f: norm(z.read(f)) for f in ARCHIVOS}
    if all(os.path.exists(f) and norm(open(f, "rb").read()) == nuevos[f] for f in ARCHIVOS):
        print("Ya estaba instalado: no hay nada que hacer.")
        return
    problemas = []
    for f, h in PRE.items():
        if h is None:
            if os.path.exists(f):
                problemas.append("ya existe " + f)
        elif not os.path.exists(f):
            problemas.append("falta " + f)
        elif hashlib.sha256(norm(open(f, "rb").read())).hexdigest() != h:
            problemas.append(f + " difiere de la versión esperada (¿cambios sin subir?)")
    if problemas:
        print("No se instaló nada:")
        for p in problemas:
            print("  -", p)
        sys.exit(1)
    for f in ARCHIVOS:
        datos = nuevos[f]
        os.makedirs(os.path.dirname(f) or ".", exist_ok=True)
        if os.path.exists(f) and b"\r\n" in open(f, "rb").read():
            datos = datos.replace(b"\n", b"\r\n")
        with open(f, "wb") as fh:
            fh.write(datos)
    print("Listo: %d archivos actualizados." % len(ARCHIVOS))


if __name__ == "__main__":
    main()
