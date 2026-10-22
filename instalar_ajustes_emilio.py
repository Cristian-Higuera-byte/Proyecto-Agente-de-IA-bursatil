"""Instalador: ajustes de Emilio (menú de usuario con iconos de línea, iconos de cuentas y un ticker más en la iconografía), sin tocar planes, candados ni billetera

Ejecutar desde la raíz del proyecto:   python instalar_ajustes_emilio.py
Idempotente, sin .bak. Cada archivo debe estar en alguna de las versiones conocidas (la actual de Cristian, o la de
una etapa intermedia del trabajo de Emilio); si alguno tiene cambios distintos, NO se instala nada y se indica cuál.
"""
import base64, hashlib, io, json, os, sys, zipfile

# Hashes de los estados de partida aceptados por archivo (None = el archivo no existía) y archivos que se eliminan.
ACEPTADAS = json.loads("{\"componentes_plataforma/barra_superior/usuario_menu.html\": [\"a4d303190bccb9b95c8315d796d3635fdccaf1eeffd889920051efff129cd11a\"], \"componentes_plataforma/conectar_cuenta/menu.py\": [\"19edef36647310637c4c3429c5e85bdd276d2ba0e386a279e8a12567398b9ca4\"], \"componentes_plataforma/iconografia/datos/ric_a_ticker.json\": [\"0e5750518a6c75d0def01eb03da3cceaedd115287dbcb9f6ba0a2ec795908a12\"]}")
ARCHIVOS = ["componentes_plataforma/barra_superior/usuario_menu.html", "componentes_plataforma/conectar_cuenta/menu.py", "componentes_plataforma/iconografia/datos/ric_a_ticker.json"]
BORRAR = []
ZIP_B64 = "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Z9mNe+qmaLDR3m7vtqMDmsMfEQcdNJVd11TeboEb0+2/9L22QX/un/2nb7Vf9r124///M3nFr38BUEsDBBQAAAAIAGSeVl0xN3cIzQIAAHYJAAA6AAAAY29tcG9uZW50ZXNfcGxhdGFmb3JtYS9pY29ub2dyYWZpYS9kYXRvcy9yaWNfYV90aWNrZXIuanNvbm2Vu3LbMBBFe3+Fx3XGM046d4sHQUQgQAMkJblJkzqTPpN/z0rC7kWR7vpgsbj7oPzn6fn5hS40va708v78YttNfLlRk9e1U5aKHeWiWGk6lrnTxSot1UuKUpVSrEIpjlRMPNzcqaVaxRoNNAilAbdQTMcsFfscou/8pgd7lNUe0qy7EX8sh0e1Hyzh21qtBpXTVprQDVZMSUmaV5LiuS4S3dXDSN0k9cmjf6vX/lUUk3xwnSbEOmpbp65dFS9RTS9pcLdftU9IEYuOwOE939JFgpGCUpPtoIS6p7KHjqcAd9+tkxzOo3mNmvhoBCPb5mVDWCLazjLFtiutPpM0KcNIK0GCQ0KOQxekq0eJ+xSlxIqdTBQk9bJgPza/6gZvHgsSvE6RJZI7L05E9iXWKl1AcjtJkhnVHKlI7ISu7iZKLMuh9CirwBI+LrNMrJ2HpurQm0XqaouunoWP2HTb44r9jYtWnk9DV6tOZvjQD3Fhy4GNjEUWxMRlwLq+BgNIm3aUhv2ou5Em1X1oh2/TTynRN7R6OTv9NuAvTPokS8XZX6RylrBSHm5vHyOetNT0FwTNI9dCvpt27dX5XiG16dftr/e7Hvg1gF+zHviS9cAXwsFilLNUPOdT+PG7H8w+f8OFaoNcqCfFbvOaiLXyFsFZK6d0SBqWyL4f8LMfX5HfnJDf4F3LvGM74Hr2glnCDa2CWaJty1kwS8VxuuibrOFlPcPLnMDn9D+cZpLsLIcWV83C+k0PpqreWQIvwAuw8VG9+4i+8MClLwXjnhE9D9FrmzHulWaM+5OSXGA5jONtGAe8t+ubNvgKvO6LYJZYgogGs0ZvsrtIPMuhNXnTC6xRV6YJF5AnYfmSx3b7yv/2jnj/GEy7qccvY44fHe8fpPhs2tHxmTdY8OYTdbydEG3XR8xtZyIwBd9eTb1XGu7qsWJ+Mx07vsfq6e/TP1BLAQIUAxQAAAAIAGSeVl3jZaUb+AYAAMwXAAA3AAAAAAAAAAAAAACAAQAAAABjb21wb25lbnRlc19wbGF0YWZvcm1hL2JhcnJhX3N1cGVyaW9yL3VzdWFyaW9fbWVudS5odG1sUEsBAhQDFAAAAAgAZJ5WXUZMUMKwBgAAThIAAC4AAAAAAAAAAAAAAIABTQcAAGNvbXBvbmVudGVzX3BsYXRhZm9ybWEvY29uZWN0YXJfY3VlbnRhL21lbnUucHlQSwECFAMUAAAACABknlZdMTd3CM0CAAB2CQAAOgAAAAAAAAAAAAAAgAFJDgAAY29tcG9uZW50ZXNfcGxhdGFmb3JtYS9pY29ub2dyYWZpYS9kYXRvcy9yaWNfYV90aWNrZXIuanNvblBLBQYAAAAAAwADACkBAABuEQAAAAA="


def norm(b):
    return b.replace(b"\r\n", b"\n")


def sha(f):
    """Hash del archivo (sin distinguir saltos de línea de Windows) o None si no existe."""
    return hashlib.sha256(norm(open(f, "rb").read())).hexdigest() if os.path.exists(f) else None


def main():
    z = zipfile.ZipFile(io.BytesIO(base64.b64decode(ZIP_B64)))
    nuevos = {f: norm(z.read(f)) for f in ARCHIVOS}
    destino = {f: hashlib.sha256(nuevos[f]).hexdigest() for f in ARCHIVOS}
    pendientes = [f for f in ARCHIVOS if sha(f) != destino[f]]
    a_borrar = [f for f in BORRAR if os.path.exists(f)]
    if not pendientes and not a_borrar:
        print("Ya estaba instalado: no hay nada que hacer.")
        return
    problemas = [f + (" ya existe con otro contenido" if sha(f) else " falta") + " o difiere de las versiones conocidas (¿cambios sin subir?)"
                 for f in pendientes if sha(f) not in ACEPTADAS[f]]
    if problemas:
        print("No se instaló nada:")
        for p in problemas:
            print("  -", p)
        sys.exit(1)
    for f in pendientes:
        datos = nuevos[f]
        os.makedirs(os.path.dirname(f) or ".", exist_ok=True)
        if os.path.exists(f) and b"\r\n" in open(f, "rb").read():
            datos = datos.replace(b"\n", b"\r\n")
        with open(f, "wb") as fh:
            fh.write(datos)
    for f in a_borrar:
        os.remove(f)
    print("Listo: %d archivos actualizados, %d eliminados." % (len(pendientes), len(a_borrar)))


if __name__ == "__main__":
    main()
