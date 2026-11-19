# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ------------------------------ INICIO Piña y Jara archivos_privados .PY -------------------------------
# -------------------------------------------------------------------------------------------------------

"""
archivos_privados.py
--------------------
Archivos que las herramientas del agente generan para un usuario (reportes y gráficos), guardados en una carpeta PRIVADA por usuario (V17 de la auditoría de seguridad).

Antes se escribían en `static/reportes` y `static/graficos`, una carpeta común a todos, con nombres que solo llevaban el segundo de creación (dos exportaciones simultáneas se pisaban y el
nombre era predecible), y el colector de imágenes del chat aceptaba cualquier ruta existente con extensión de imagen. Ahora:

  - Todo va a `data/archivos_usuarios/<usuario>/<reportes|graficos>/`, fuera de `static` y de cualquier carpeta que se sirva por la web, con permisos solo del propietario.
  - El nombre del archivo es un identificador aleatorio de 128 bits (`secrets.token_urlsafe`): no se puede adivinar ni se repite entre exportaciones simultáneas.
  - Un archivo solo se acepta (para mostrarlo o descargarlo) si, ya resuelta su ruta real (sin enlaces simbólicos ni `..`), está DENTRO de la carpeta del usuario que lo pide, es un archivo normal,
    tiene una extensión permitida y no supera el tamaño máximo. La propiedad la da la carpeta: un usuario no puede pedir el archivo de otro aunque conozca su ruta.
  - Retención: los archivos vencen a los `retencion_dias` días y cada usuario conserva como máximo `maximo_por_usuario` (se borran los más antiguos).
"""
import os
import re
import secrets
import time
from pathlib import Path

import configuracion
from nucleo_agente import contexto

EXTENSIONES_IMAGEN = (".png", ".jpg", ".jpeg", ".webp")
EXTENSIONES_REPORTE = (".md", ".html", ".csv")
CATEGORIAS = ("reportes", "graficos")


# TITULO RAIZ

def raiz() -> Path:
    """Carpeta que contiene las carpetas privadas de todos los usuarios (fuera de `static`)."""
    return Path(configuracion.DIR_DATOS) / "archivos_usuarios"


# TITULO SEGMENTO DE USUARIO

def _segmento_usuario(usuario_id) -> str:
    """Nombre de carpeta del usuario: solo letras, números, guion y guion bajo (nunca puede llevar `.`, `/` ni `\\`, así que no escapa de la carpeta raíz). Vacío se trata como «local»."""
    texto = re.sub(r"[^A-Za-z0-9_-]", "_", str("local" if usuario_id in (None, "") else usuario_id))[:40]
    return texto or "local"


# TITULO USUARIO DE LA CONSULTA

def _usuario(usuario_id) -> str:
    """El usuario indicado o, si no se indica, el de la consulta del agente en curso (contexto del hilo)."""
    return usuario_id if usuario_id is not None else contexto.usuario_actual()


# TITULO RESTRINGIR

def _restringir(ruta: Path) -> None:
    """Deja una carpeta accesible solo para su propietario (no tiene efecto en Windows)."""
    try:
        os.chmod(ruta, 0o700)
    except OSError:
        pass


# TITULO CARPETA DE

def carpeta_de(usuario_id=None, categoria: str = "reportes", crear: bool = True) -> Path:
    """Carpeta privada del usuario para una categoría («reportes» o «graficos»); la crea con permisos solo del propietario si hace falta."""
    if categoria not in CATEGORIAS:
        raise ValueError(f"categoría de archivo no válida: {categoria}")
    carpeta = raiz() / _segmento_usuario(_usuario(usuario_id)) / categoria
    if crear:
        carpeta.mkdir(parents=True, exist_ok=True)
        for c in (carpeta.parent, carpeta):
            _restringir(c)
    return carpeta


# TITULO NUEVO ARCHIVO

def nuevo_archivo(categoria: str, extension: str, usuario_id=None) -> Path:
    """Ruta de un archivo NUEVO en la carpeta privada del usuario, con nombre aleatorio. Antes de entregarla aplica la retención. No crea el archivo: quien llama lo escribe."""
    extension = extension.lower()
    if extension not in EXTENSIONES_IMAGEN + EXTENSIONES_REPORTE:
        raise ValueError(f"extensión de archivo no permitida: {extension}")
    carpeta = carpeta_de(usuario_id, categoria)
    limpiar_vencidos(usuario_id)
    return carpeta / (secrets.token_urlsafe(16) + extension)


# TITULO RUTA AUTORIZADA

def ruta_autorizada(ruta, usuario_id=None, extensiones: tuple | None = None) -> Path | None:
    """Ruta real del archivo si el usuario puede usarlo, o None.

    Exige que sea un archivo normal que NO sea un enlace simbólico, que su ruta ya resuelta esté dentro de la carpeta del usuario (no de otro, ni fuera del espacio de archivos), que la extensión
    sea una de `extensiones` (por defecto imágenes y reportes) y que no pase del tamaño máximo. Cualquier error (ruta rara, archivo que no existe) devuelve None."""
    permitidas = extensiones or (EXTENSIONES_IMAGEN + EXTENSIONES_REPORTE)
    try:
        candidata = Path(ruta)
        if candidata.is_symlink():
            return None
        real = candidata.resolve(strict=True)
        base = (raiz() / _segmento_usuario(_usuario(usuario_id))).resolve()
        if base not in real.parents or real.suffix.lower() not in permitidas or not real.is_file():
            return None
        if real.stat().st_size > int(configuracion.ARCHIVOS_USUARIO["tamano_maximo_mb"]) * 1024 * 1024:
            return None
        return real
    except (OSError, ValueError, TypeError, RuntimeError):
        return None


# TITULO LEER

def leer(ruta, usuario_id=None, extensiones: tuple | None = None) -> bytes | None:
    """Contenido del archivo si `ruta_autorizada` lo permite para ese usuario (es la autorización de cada descarga); None si no."""
    real = ruta_autorizada(ruta, usuario_id, extensiones)
    if real is None:
        return None
    try:
        return real.read_bytes()
    except OSError:
        return None


# TITULO LIMPIAR VENCIDOS

def limpiar_vencidos(usuario_id=None) -> int:
    """Aplica la retención a los archivos del usuario: borra los de más de `retencion_dias` días y, si quedan más de `maximo_por_usuario`, los más antiguos. Devuelve cuántos borró."""
    dias, maximo = int(configuracion.ARCHIVOS_USUARIO["retencion_dias"]), int(configuracion.ARCHIVOS_USUARIO["maximo_por_usuario"])
    limite, borrados, vigentes = time.time() - dias * 86400, 0, []
    for categoria in CATEGORIAS:
        carpeta = carpeta_de(usuario_id, categoria, crear=False)
        if not carpeta.is_dir():
            continue
        for archivo in carpeta.iterdir():
            try:
                if archivo.is_symlink() or not archivo.is_file():
                    continue
                if archivo.stat().st_mtime < limite:
                    archivo.unlink()
                    borrados += 1
                else:
                    vigentes.append((archivo.stat().st_mtime, archivo))
            except OSError:
                continue
    for _, archivo in sorted(vigentes, key=lambda x: x[0], reverse=True)[maximo:]:
        try:
            archivo.unlink()
            borrados += 1
        except OSError:
            pass
    return borrados


# -------------------------------------------------------------------------------------------------------
# ------------------------------- FIN Piña y Jara archivos_privados .PY ---------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
