"""Script TEMPORAL: genera el esquema actual de la base (pg_dump), lo limpia para que se pueda pegar y ejecutar, lo PRUEBA ejecutándolo en un esquema temporal con ROLLBACK y guarda el archivo
limpio en ~/base_datos_limpia.sql. Se borra después de usarlo. No lee ni guarda datos ni claves: solo la estructura.
Uso (desde la carpeta del proyecto, en el servidor):  python probar_bd.py
"""
import os
import re
import subprocess

from dotenv import dotenv_values

v = dotenv_values(".env")
entorno = dict(os.environ, PGPASSWORD=v["POSTGRES_CONTRASENA"])
h = ["-h", v["POSTGRES_SERVIDOR"], "-p", v.get("POSTGRES_PUERTO") or "5432", "-U", v["POSTGRES_USUARIO"], "-d", v["POSTGRES_BASE_DATOS"], "--no-password"]
volcado = subprocess.run(["pg_dump", *h, "--schema-only"], capture_output=True, text=True, env=entorno).stdout
quitar = re.compile(r"^(CREATE EXTENSION|COMMENT ON EXTENSION|SELECT pg_catalog\.set_config\('search_path'|ALTER .* OWNER TO )")
lineas = volcado.split("\n")
limpio = "\n".join(linea for linea in lineas if not quitar.match(linea))
ruta = os.path.expanduser("~/base_datos_limpia.sql")
with open(ruta, "w", encoding="utf-8", newline="\n") as f:
    f.write(limpio)
guion = ("BEGIN;\nCREATE SCHEMA prueba_v;\n" + limpio.replace("public.", "prueba_v.") +
         "\nSELECT 'tablas' AS que, count(*) FROM information_schema.tables WHERE table_schema = 'prueba_v' UNION ALL "
         "SELECT 'funciones', count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace WHERE n.nspname = 'prueba_v' UNION ALL "
         "SELECT 'columna credencial_version', count(*) FROM information_schema.columns WHERE table_schema = 'prueba_v' AND column_name = 'credencial_version';\nROLLBACK;\n")
r = subprocess.run(["psql", *h, "-v", "ON_ERROR_STOP=1", "-At", "-f", "-"], input=guion, capture_output=True, text=True, env=entorno)
print("lineas del volcado:", len(lineas), "| quitadas:", len(lineas) - len(limpio.split("\n")))
print("codigo de psql:", r.returncode)
print("resultado:", [x for x in r.stdout.split("\n") if "|" in x])
print("ERRORES:", r.stderr[-400:] or "ninguno")
restante = subprocess.run(["psql", *h, "-At", "-c", "SELECT count(*) FROM pg_namespace WHERE nspname = 'prueba_v'"], capture_output=True, text=True, env=entorno).stdout.strip()
print("esquema temporal restante:", restante)
print("el archivo limpio tiene el codigo de V18:", "credencial_version" in limpio, "| tablas:", limpio.count("\nCREATE TABLE "), "| GRANT/REVOKE:", len(re.findall(r"^(GRANT|REVOKE)", limpio, re.M)), "| OWNER TO:", limpio.count("OWNER TO"))
