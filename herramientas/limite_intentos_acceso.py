# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# --------------------------- INICIO Piña y Jara limite_intentos_acceso .PY -----------------------------
# -------------------------------------------------------------------------------------------------------

"""
limite_intentos_acceso.py
-------------------------
Límite persistente de intentos de inicio de sesión, por cuenta y por dirección IP (V08 de la auditoría).

reCAPTCHA frena a los robots, pero no impide que alguien pruebe contraseñas sin parar contra una cuenta. Aquí se cuentan los intentos en una ventana de tiempo y, al pasar el tope,
se rechaza el intento SIN mirar la contraseña (así acertar durante el bloqueo tampoco sirve):
  * por CUENTA: 5 intentos cada 15 minutos. Se cuenta el correo escrito aunque no exista, así que una cuenta inexistente se bloquea igual que una real y el bloqueo no revela nada.
  * por IP: 20 intentos cada 15 minutos (cubre a quien prueba muchas cuentas desde un mismo lugar; es más alto porque varias personas pueden compartir una IP).

El intento se anota ANTES de verificar la contraseña (así varias pruebas simultáneas también cuentan) y, si la contraseña era correcta, se borra: iniciar sesión bien nunca consume el cupo
y limpia los fallos de esa cuenta. Los correos no se guardan: solo su resumen SHA-256.

Compromiso aceptado: quien conoce el correo de otra persona puede bloquearle el ingreso por contraseña durante 15 minutos (no el ingreso con Google ni la recuperación de contraseña).

El estado vive en un archivo SQLite propio (data/intentos_acceso.db) para que lo vean todos los procesos y sobreviva a los reinicios.
"""
import hashlib
import os
import sqlite3
import sys
import threading
import time
from contextlib import closing
from pathlib import Path

DIR_DATOS = Path(__file__).resolve().parent.parent / "data"
RUTA_DB = DIR_DATOS / "intentos_acceso.db"

# Ventana de conteo, en segundos, y topes de intentos dentro de ella
VENTANA = 15 * 60
MAX_POR_CUENTA = 5
MAX_POR_IP = 20

# Cuántos proxies de confianza hay entre el navegador y Streamlit (variable PROXIES_CONFIABLES del .env). En el cPanel hay uno: el Apache de Netexplora. Si hubiera una CDN delante
# de Apache serían dos; con un número mal puesto TODAS las personas parecerían venir de la misma IP, por eso el primer uso deja en el log lo que llegó.
PROXIES_CONFIABLES = max(1, int(os.getenv("PROXIES_CONFIABLES", "1") or "1"))

_PREPARADA: Path | None = None
_CANDADO = threading.Lock()
_REGISTRADA_IP = False


# TITULO CONECTAR

def _conectar() -> sqlite3.Connection:
    """Abre una conexión nueva al archivo de intentos (lo crea con su tabla la primera vez en este proceso). Quien la llama debe cerrarla."""
    global _PREPARADA
    DIR_DATOS.mkdir(exist_ok=True)
    con = sqlite3.connect(RUTA_DB, timeout=10, isolation_level=None)       # sin transacción automática: `comenzar` abre la suya con BEGIN IMMEDIATE
    if _PREPARADA != RUTA_DB:
        with _CANDADO:
            con.execute("CREATE TABLE IF NOT EXISTS intentos (id INTEGER PRIMARY KEY AUTOINCREMENT, clave TEXT NOT NULL, momento REAL NOT NULL)")
            con.execute("CREATE INDEX IF NOT EXISTS intentos_clave ON intentos (clave, momento)")
            _PREPARADA = RUTA_DB
    return con


# TITULO HUELLA

def _huella(texto: str) -> str:
    """Resumen SHA-256 del texto (correo normalizado): así el archivo no guarda correos."""
    return hashlib.sha256((texto or "").strip().lower().encode("utf-8")).hexdigest()


# TITULO ESPERA

def _espera(con: sqlite3.Connection, clave: str, tope: int, ahora: float) -> int:
    """Segundos que faltan para que `clave` baje del tope de intentos (0 si todavía tiene cupo)."""
    momentos = [f[0] for f in con.execute("SELECT momento FROM intentos WHERE clave = ? AND momento > ? ORDER BY momento", (clave, ahora - VENTANA)).fetchall()]
    if len(momentos) < tope:
        return 0
    return max(1, int(momentos[len(momentos) - tope] + VENTANA - ahora) + 1)


# TITULO COMENZAR

def comenzar(correo: str, ip: str | None) -> dict:
    """Pide cupo para un intento de inicio de sesión de ese correo desde esa IP.

    Devuelve {"bloqueado": segundos} si alguno de los dos topes está lleno (no anota nada: un bloqueo no se alarga por insistir), o {"bloqueado": 0, "ids": [...]} con los
    registros del intento, que hay que pasar a `exito` si la contraseña era correcta."""
    ahora = time.time()
    claves = [f"cuenta:{_huella(correo)}"] + ([f"ip:{ip}"] if ip else [])
    topes = [MAX_POR_CUENTA] + ([MAX_POR_IP] if ip else [])
    with closing(_conectar()) as con:
        con.execute("BEGIN IMMEDIATE")                       # tomar el cupo es atómico: dos intentos simultáneos no pasan ambos por el último lugar
        try:
            con.execute("DELETE FROM intentos WHERE momento < ?", (ahora - VENTANA,))
            espera = max(_espera(con, c, t, ahora) for c, t in zip(claves, topes))
            if espera:
                con.execute("COMMIT")
                return {"bloqueado": espera}
            ids = [con.execute("INSERT INTO intentos (clave, momento) VALUES (?, ?)", (c, ahora)).lastrowid for c in claves]
            con.execute("COMMIT")
            return {"bloqueado": 0, "ids": ids}
        except Exception:
            con.execute("ROLLBACK")
            raise


# TITULO EXITO

def exito(correo: str, ids: list) -> None:
    """La contraseña era correcta: devuelve el cupo de este intento y borra los fallos anteriores de esa cuenta (los de la IP se vencen solos)."""
    with closing(_conectar()) as con:
        if ids:
            con.execute(f"DELETE FROM intentos WHERE id IN ({','.join('?' * len(ids))})", ids)
        con.execute("DELETE FROM intentos WHERE clave = ?", (f"cuenta:{_huella(correo)}",))


# TITULO MENSAJE

def mensaje(segundos: int) -> str:
    """Texto para la persona cuando se pasó del tope: el mismo para cuentas que existen y que no."""
    minutos = max(1, -(-int(segundos) // 60))
    return f"Demasiados intentos. Espera {minutos} minuto{'s' if minutos != 1 else ''} antes de volver a intentarlo."


# TITULO IP CLIENTE

def ip_cliente(cabeceras) -> str | None:
    """Dirección de quien se conecta, a partir de las cabeceras que llegan a Streamlit; None si no se puede saber.

    Detrás de los proxies de confianza, cada uno añade al FINAL de `X-Forwarded-For` la dirección que vio conectarse. Con un proxy (Apache) la última es la real; con N proxies es
    la N-ésima contando desde el final. Las anteriores las puede inventar el cliente (manda su propia cabecera y el proxy solo agrega la suya), así que no se usan.
    La primera vez en cada proceso deja en el log lo que llegó y la dirección elegida, para comprobar que `PROXIES_CONFIABLES` está bien."""
    global _REGISTRADA_IP
    try:
        crudo = cabeceras.get("X-Forwarded-For") or ""
    except Exception:  # noqa: BLE001 - sin contexto de petición (pruebas, otro proceso)
        return None
    partes = [p.strip() for p in crudo.split(",") if p.strip()]
    ip = partes[-PROXIES_CONFIABLES][:64] if len(partes) >= PROXIES_CONFIABLES else None
    if not _REGISTRADA_IP:
        _REGISTRADA_IP = True
        print(f"[Acceso] X-Forwarded-For recibido: «{crudo[:200]}» · proxies de confianza: {PROXIES_CONFIABLES} · IP usada: {ip}", file=sys.stderr, flush=True)
    return ip


# -------------------------------------------------------------------------------------------------------
# ---------------------------- FIN Piña y Jara limite_intentos_acceso .PY -------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
