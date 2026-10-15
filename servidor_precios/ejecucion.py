"""Arranque del servidor de datos (hilo del motor + servidor HTTP)."""
import threading

from http.server import ThreadingHTTPServer

from herramientas.puente_mt5 import inicializar_mt5

from .constantes import INTERVALO_TICKS, PUERTO
from .manejador import Manejador
from .motor import MOTOR


def ejecutar() -> None:
    inicializar_mt5()
    threading.Thread(target=MOTOR.correr, name="motor-precios", daemon=True).start()
    servidor = ThreadingHTTPServer(("127.0.0.1", PUERTO), Manejador)
    servidor.daemon_threads = True
    print(f"Servidor de datos MT5 activo en http://localhost:{PUERTO}  (Ctrl+C para detener)")
    print(f"  · Precios en vivo por SSE cada {int(INTERVALO_TICKS * 1000)} ms  (/stream)")
    servidor.serve_forever()
