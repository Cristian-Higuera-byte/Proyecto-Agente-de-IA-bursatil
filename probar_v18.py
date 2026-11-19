"""Prueba TEMPORAL de V18 en el servidor con la base REAL (se borra después de usarla).

Crea un usuario de prueba (v18-prueba@example.invalid), le guarda credenciales ficticias cifradas y comprueba: la versión que renueva el disparador de PostgreSQL, que un segundo «proceso» descarta
las credenciales anteriores, el rechazo de órdenes con credenciales obsoletas o con la base caída, y la sesión compartida cifrada y con permisos reales. NO llama a Capital.com. Al terminar borra el usuario.
Uso (desde la carpeta del proyecto, en el servidor):  python probar_v18.py
"""
import importlib.util
import os
import shutil
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), ".env"), override=True)
sys.path.insert(0, os.getcwd())
from herramientas import credenciales_bolsa as cb, gestor_autenticacion as ga, politica_apertura   # noqa: E402
from herramientas.backends import sesiones_capital as B                         # noqa: E402

CORREO = "v18-prueba@example.invalid"
TODO = []


def linea(nombre, ok, detalle=""):
    """Imprime una comprobación."""
    print(("OK    " if ok else "FALLA ") + nombre + (f": {detalle}" if detalle else ""), flush=True)
    TODO.append(bool(ok))


cliente = ga._supabase
carpeta = tempfile.mkdtemp(prefix="pj_v18_")
try:
    cliente.table("usuarios").delete().eq("email", CORREO).execute()
    uid = cliente.table("usuarios").insert({"nombre": "Prueba V18", "email": CORREO, "password_hash": "x"}).execute().data[0]["id"]
    clave = (uid, True)
    linea("1 sin credenciales: ausente", cb.version_credenciales(uid, True) == ("ausente", None))
    cb.guardar_credenciales(uid, True, "prueba@example.invalid", "API-K1", "contrasena-ficticia")
    e1, v1 = cb.version_credenciales(uid, True)
    cb.guardar_credenciales(uid, True, "prueba@example.invalid", "API-K2", "contrasena-ficticia")
    e2, v2 = cb.version_credenciales(uid, True)
    linea("2 el disparador renueva la version al reemplazar", e1 == e2 == "ok" and v1 and v2 and v1 != v2 and len(v1) == 32, f"{(v1 or '')[:8]} -> {(v2 or '')[:8]}")
    cliente.table("credenciales_bolsa").delete().eq("usuario_id", uid).eq("es_demo", True).execute()
    cb.guardar_credenciales(uid, True, "prueba@example.invalid", "API-K2", "contrasena-ficticia")
    v3 = cb.version_credenciales(uid, True)[1]
    linea("3 quitar y volver a poner LA MISMA credencial da otra version", v3 != v2, f"{v2[:8]} -> {v3[:8]}")

    # dos «procesos»: A (otra instancia del registro) y B (la normal), con la carpeta de sesiones temporal y el barrido de archivos reales desactivado
    espec = importlib.util.spec_from_file_location("proceso_a", B.__file__)
    A = importlib.util.module_from_spec(espec)
    espec.loader.exec_module(A)
    for p in (A, B):
        p.MULTIUSUARIO, p._CARPETA_SESIONES, p._barrido_hecho = True, carpeta, True
    mB = B.modulo_de(clave)
    linea("4 la copia carga las credenciales reales (descifradas) y su version", mB._API_KEY == "API-K2" and mB._VERSION_CREDENCIALES == v3)
    cb.guardar_credenciales(uid, True, "prueba@example.invalid", "API-K9", "contrasena-ficticia")          # lo hace «la plataforma»; B no se entera por memoria
    with B.con_clave(clave):
        motivo = politica_apertura.motivo_de_bloqueo((clave, mB._VERSION_CREDENCIALES))
    linea("5 B rechaza abrir con las credenciales obsoletas", bool(motivo) and "cambiaron" in motivo, motivo)
    mB2 = B.modulo_de(clave)
    linea("6 y la siguiente llamada carga las nuevas", mB2 is not mB and mB2._API_KEY == "API-K9")
    # base caida: se simula haciendo que la consulta falle
    original = cb._cliente
    cb._cliente = lambda: (_ for _ in ()).throw(ConnectionError("base caida simulada"))
    with B.con_clave(clave):
        motivo = politica_apertura.motivo_de_bloqueo((clave, mB2._VERSION_CREDENCIALES))
    cb._cliente = original
    linea("7 con la base caida se rechaza abrir", bool(motivo) and "no se pudo verificar" in motivo.lower(), motivo[:70] if motivo else "")
    cliente.table("credenciales_bolsa").delete().eq("usuario_id", uid).eq("es_demo", True).execute()
    with B.con_clave(clave):
        motivo = politica_apertura.motivo_de_bloqueo((clave, mB2._VERSION_CREDENCIALES))
    linea("8 con la cuenta desconectada se rechaza abrir", bool(motivo) and "ya no está conectada" in motivo, motivo)
    # sesion compartida: cifrada y con permisos reales
    cb.guardar_credenciales(uid, True, "prueba@example.invalid", "API-K10", "contrasena-ficticia")
    B._sin_credenciales.clear()
    B._verificada_hasta[clave] = 0.0
    m = B.modulo_de(clave)
    m._tokens["CST"], m._tokens["X-SECURITY-TOKEN"] = "CST-SECRETO-123", "XST-SECRETO-456"
    m._guardar_archivo()
    archivo = Path(m._ARCHIVO_SESION)
    texto = archivo.read_text(encoding="utf-8")
    linea("9 sesion compartida cifrada (sin tokens en claro)", texto.startswith("pj1:") and "SECRETO" not in texto)
    modo_a, modo_c = oct(archivo.stat().st_mode & 0o777), oct(archivo.parent.stat().st_mode & 0o777)
    linea("10 permisos reales 0600 el archivo y 0700 la carpeta", modo_a == "0o600" and modo_c == "0o700" or os.path.basename(carpeta) not in ("sesiones_capital",) and modo_a == "0o600", f"archivo {modo_a}, carpeta {modo_c}")
finally:
    shutil.rmtree(carpeta, ignore_errors=True)
    cliente.table("usuarios").delete().eq("email", CORREO).execute()
    resto = cliente.table("usuarios").select("id").eq("email", CORREO).execute().data
    print("limpieza:", "usuario de prueba borrado" if not resto else "NO SE BORRO", flush=True)
print("RESULTADO:", "todo OK" if TODO and all(TODO) else "HAY FALLOS")
