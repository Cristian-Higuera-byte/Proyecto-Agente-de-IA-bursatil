"""Rutas HTTP del servidor: GET (velas, ticks, símbolos, salud), SSE (/stream) y POST (SL/TP y órdenes)."""
import json
import time
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, unquote, urlparse

from herramientas.puente_mt5 import (colocar_orden_pendiente, ejecutar_orden_mercado, eliminar_orden,
                                     modificar_orden, modificar_sltp)

from .constantes import CANDADO_MT5, PING_SSE, VERSION_API
from .motor import MOTOR
from .simbolos import listar_simbolos
from .velas import obtener_velas


def _lista_simbolos(qs) -> list:
    crudo = qs.get("s", [""])[0]
    return [s for s in (x.strip() for x in crudo.split(",")) if s][:80]


class Manejador(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _origen_permitido(self):
        """El Origin de la petición si es una página de este equipo (el dashboard en localhost); si no, None."""
        origen = self.headers.get("Origin", "") or ""
        host = urlparse(origen).hostname
        return origen if host in ("localhost", "127.0.0.1") else None

    def _cabecera_cors(self):
        """CORS solo para el dashboard local: otra web abierta en el navegador no puede leer
        saldo, equidad ni posiciones de esta API."""
        origen = self._origen_permitido()
        if origen:
            self.send_header("Access-Control-Allow-Origin", origen)
            self.send_header("Vary", "Origin")

    def _responder(self, obj):
        cuerpo = json.dumps(obj).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(cuerpo)))
        self._cabecera_cors()   # permite el fetch desde el iframe del gráfico (solo localhost)
        self.end_headers()
        self.wfile.write(cuerpo)

    def _stream(self, simbolos):
        """SSE: envía la foto completa y luego solo los cambios, hasta que el
        navegador cierre la conexión."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self._cabecera_cors()
        self.end_headers()
        MOTOR.suscribir(simbolos)
        seq = 0
        ultimo_envio = time.time()
        try:
            self.wfile.write(b"retry: 2000\n\n")
            while True:
                nuevo, ticks, cuenta = MOTOR.foto(simbolos, seq)
                seq = nuevo
                if ticks or cuenta:
                    msg = {"t": ticks}
                    if cuenta:
                        msg["acc"] = cuenta
                    self.wfile.write(b"data: " + json.dumps(msg).encode("utf-8") + b"\n\n")
                    self.wfile.flush()
                    ultimo_envio = time.time()
                elif time.time() - ultimo_envio >= PING_SSE:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    ultimo_envio = time.time()
                MOTOR.suscribir(simbolos)          # mantiene viva la suscripción
                MOTOR.esperar(seq, timeout=PING_SSE)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass   # el navegador cerró la pestaña o cambió de vista

    def do_GET(self):
        parsed = urlparse(self.path)
        partes = [unquote(p) for p in parsed.path.strip("/").split("/")]
        qs = parse_qs(parsed.query)
        tf = qs.get("tf", ["H1"])[0]
        try:
            if partes and partes[0] == "stream":
                self._stream(_lista_simbolos(qs))
            elif partes and partes[0] == "ticks":
                simbolos = _lista_simbolos(qs)
                MOTOR.suscribir(simbolos)
                _, ticks, cuenta = MOTOR.foto(simbolos, 0)
                self._responder({"t": ticks, "acc": cuenta})
            elif partes and partes[0] == "simbolos":
                self._responder(listar_simbolos())
            elif partes and partes[0] == "salud":
                self._responder({"ok": True, "v": VERSION_API})
            elif len(partes) >= 2 and partes[0] == "velas":
                n = int(qs.get("n", ["150"])[0])
                self._responder(obtener_velas(partes[1], tf, n))
            elif len(partes) >= 2 and partes[0] == "ultima":
                velas = obtener_velas(partes[1], tf, 2)
                self._responder(velas[-1] if velas else {})
            else:
                self._responder({"error": "ruta no reconocida"})
        except Exception as e:
            try:
                self._responder({"error": str(e)})
            except Exception:
                pass

    # --- Modificaciones (POST) ----------------------------------------------
    def _origen_local(self) -> bool:
        """Solo páginas servidas desde este equipo (el dashboard en localhost) pueden
        modificar posiciones: otra web abierta en el navegador no puede."""
        host = urlparse(self.headers.get("Origin", "") or "").hostname
        return host in ("localhost", "127.0.0.1")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cabecera_cors()
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        if not self._origen_local():
            cuerpo = b'{"error": "origen no permitido"}'
            self.send_response(403)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)
            return
        try:
            n = int(self.headers.get("Content-Length", 0) or 0)
            datos = json.loads(self.rfile.read(n) or b"{}")
            ruta = urlparse(self.path).path.strip("/")
            with CANDADO_MT5:   # mismo candado que el motor: la API de MT5 no es thread-safe
                if ruta == "sltp":
                    res = modificar_sltp(int(datos["ticket"]), datos.get("sl"), datos.get("tp"))
                elif ruta == "orden":
                    res = colocar_orden_pendiente(datos["symbol"], datos["lado"],
                                                  float(datos["volumen"]), float(datos["precio"]))
                elif ruta == "orden/modificar":
                    res = modificar_orden(int(datos["ticket"]), datos.get("precio"),
                                          datos.get("sl"), datos.get("tp"),
                                          datos.get("caducidad"), datos.get("expiracion"))
                elif ruta == "orden/eliminar":
                    res = eliminar_orden(int(datos["ticket"]))
                elif ruta == "mercado":
                    lado = str(datos.get("lado", "")).upper()
                    vol = float(datos["volumen"])
                    if lado not in ("BUY", "SELL") or not vol > 0:
                        res = {"error": "Orden a mercado no válida (lado o volumen)"}
                    else:
                        res = ejecutar_orden_mercado(str(datos["symbol"]), lado, vol)
                else:
                    res = None
            if res is not None:
                self._responder(res)
            else:
                self._responder({"error": "ruta no reconocida"})
        except Exception as e:
            try:
                self._responder({"error": str(e)})
            except Exception:
                pass

    def log_message(self, *args):
        pass  # silencia los logs de acceso en consola
