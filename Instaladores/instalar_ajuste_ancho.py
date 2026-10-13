"""Arregla el eje de precios cortado cuando el gráfico se estrecha (panel lateral derecho abierto, cambio de opción).

USO: copia este archivo a la RAIZ de tu proyecto (donde esta app.py) y ejecutalo:
        python instalar_ajuste_ancho.py
Actualiza 3 archivos CSS de components/grafico/estatico/css/ (guarda copia .bak). Despues recarga Streamlit (F5 o reinicio).
"""
import base64, io, os, shutil, sys, zipfile

ZIP_B64 = """
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
"""


def main():
    if not os.path.isfile("app.py") or not os.path.isdir(os.path.join("components", "grafico")):
        sys.exit("Ejecuta este archivo desde la RAIZ del proyecto (donde estan app.py y components/grafico).")
    z = zipfile.ZipFile(io.BytesIO(base64.b64decode("".join(ZIP_B64.split()))))
    for nombre in z.namelist():
        destino = nombre.replace("/", os.sep)
        if os.path.exists(destino):
            shutil.copy2(destino, destino + ".bak")
        with open(destino, "wb") as f:
            f.write(z.read(nombre))
        print("actualizado:", nombre)
    print("Listo. Recarga Streamlit.")


if __name__ == "__main__":
    main()
