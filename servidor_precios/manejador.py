# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ----------------------------------- INICIO Piña y Jara manejador .PY ----------------------------------
# -------------------------------------------------------------------------------------------------------

"""Rutas HTTP del servidor: GET (velas, ticks, símbolos, salud), SSE (/stream) y POST (SL/TP y órdenes).

Define `Manejador`, el BaseHTTPRequestHandler que usa ejecucion.py. Los GET solo leen datos
del motor o del broker; los POST modifican posiciones/órdenes y solo se aceptan desde páginas
de los orígenes permitidos (protección CORS/Origin) y bajo CANDADO_MT5.

LÍMITES Y ERRORES (V04): tamaño del cuerpo, tiempo por conexión, conexiones y streams simultáneos y frecuencia por cuenta viven en
limites.py; los datos de cada orden se validan antes de llamar al bróker (400). Ante una excepción el cliente recibe un mensaje
neutro con un ID de correlación (el detalle queda solo en el registro del servidor) y cada acción de trading queda en la auditoría.

MULTIUSUARIO: con `CAPITAL_MULTIUSUARIO` encendido cada petición debe traer la cookie de sesión `pj_sesion` (HttpOnly, la emite este mismo servidor; ver herramientas/boleto_sesion.py) y
la cuenta que se usa dentro de la dirección (`/t/demo/stream?...` o `/t/real/...`); sin sesión válida responde 401 (salvo /salud). La cookie se valida contra la sesión guardada en la base
(herramientas/sesion_persistente.py), de modo que cerrar la sesión la invalida al instante. La sesión dice quién es el usuario y la dirección con qué cuenta (demo o real) opera: la petición
entera se ejecuta con la sesión de Capital.com, el motor y las carpetas de datos de ESA cuenta, nunca con las de otra.
`POST /t/sesion` canjea un boleto de un solo uso por la cookie (Set-Cookie) y `POST /t/sesion/cerrar` la borra.
"""
import json
import os
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, unquote, urlparse

from herramientas import boleto_sesion, idempotencia_ordenes, sesion_persistente
from herramientas.backends import sesiones_capital
from herramientas.puente_mt5 import (colocar_orden_pendiente, ejecutar_orden_mercado, eliminar_orden,
                                     modificar_orden, modificar_sltp)

from herramientas.tickets import ticket as _tk
from . import limites
from .constantes import CANDADO_MT5, HOSTS_PERMITIDOS, PING_SSE, VERSION_API
from .motor import MOTORES
from .simbolos import listar_simbolos
from .velas import obtener_ultima, obtener_velas, precalentar


# Cada cuántos segundos una conexión de precios en vivo vuelve a comprobar que la sesión sigue vigente
REVISION_STREAM_S = 5

# Segundos que se recuerda el resultado de comprobar una sesión antes de volver a preguntar a la base: cerrar sesión corta el acceso en ese tiempo
MEMORIA_SESION_S = 5

# Contadores compartidos por todas las peticiones: frecuencia por cuenta, streams abiertos por cuenta y conexiones abiertas en total
_FRECUENCIA = limites.Frecuencia()
_STREAMS = limites.StreamsAbiertos()
_CONEXIONES = threading.BoundedSemaphore(limites.MAX_CONEXIONES)


# TITULO LISTA SIMBOLOS

def _lista_simbolos(qs) -> list:
    """Extrae del query string el parámetro `s` (símbolos separados por comas).

    Recibe el dict de parse_qs y devuelve una lista sin vacíos ni espacios, limitada a 80
    símbolos para acotar la carga del motor.
    """
    crudo = qs.get("s", [""])[0]
    return [s for s in (x.strip() for x in crudo.split(",")) if s][:80]


# TITULO MANEJADOR

class Manejador(BaseHTTPRequestHandler):
    """Atiende las peticiones HTTP del dashboard: JSON, SSE, CORS restringido a localhost y POST de trading.

    Una instancia por petición (ThreadingHTTPServer). Delega los datos en vivo en el motor de la cuenta del usuario.
    """

    # HTTP/1.1 es necesario para mantener abierta la conexión del flujo SSE
    protocol_version = "HTTP/1.1"

    # Segundos máximos sin leer o escribir en la conexión: corta a los clientes lentos o colgados (el SSE escribe seguido, no se ve afectado)
    timeout = limites.TIEMPO_ESPERA_CONEXION

    # TITULO HANDLE

    def handle(self):
        """Atiende la conexión solo si hay cupo (MAX_CONEXIONES); si no, responde 503 y la cierra sin leer nada."""
        if not _CONEXIONES.acquire(blocking=False):
            try:
                cuerpo = json.dumps({"error": limites.MENSAJE_DEMASIADAS}).encode("utf-8")
                self.wfile.write(b"HTTP/1.1 503 Service Unavailable\r\nContent-Type: application/json\r\nRetry-After: 5\r\nConnection: close\r\nContent-Length: "
                                 + str(len(cuerpo)).encode() + b"\r\n\r\n" + cuerpo)
            except OSError:
                pass
            self.close_connection = True
            return
        try:
            super().handle()
        finally:
            _CONEXIONES.release()

    # TITULO ORIGEN PERMITIDO

    def _origen_permitido(self):
        """El Origin de la petición si es una página permitida (el dashboard en localhost o los dominios de SERVIDOR_ORIGENES); si no, None."""
        origen = self.headers.get("Origin", "") or ""
        host = urlparse(origen).hostname
        return origen if host in HOSTS_PERMITIDOS else None

    # TITULO CABECERA CORS

    def _cabecera_cors(self):
        """CORS solo para el dashboard (local o de los dominios permitidos): otra web abierta en el navegador
        no puede leer saldo, equidad ni posiciones de esta API."""
        origen = self._origen_permitido()
        if origen:
            self.send_header("Access-Control-Allow-Origin", origen)
            self.send_header("Access-Control-Allow-Credentials", "true")     # el navegador manda la cookie de sesión (en producción la página y el servidor comparten dominio)
            self.send_header("Vary", "Origin")

    # TITULO RESPONDER

    def _responder(self, obj, cookie=None):
        """Envía `obj` serializado como JSON con estado 200 y cabecera CORS (si el origen es local); con `cookie` agrega esa cabecera `Set-Cookie`."""
        # Serializa a bytes UTF-8 para calcular Content-Length exacto
        cuerpo = json.dumps(obj).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")     # datos de la cuenta: ni el navegador ni un proxy los guardan
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self._cabecera_cors()   # permite el fetch desde el iframe del gráfico (solo localhost)
        self.end_headers()
        self.wfile.write(cuerpo)

    # TITULO RECHAZAR

    def _rechazar(self, codigo, mensaje):
        """Responde un error HTTP (por ejemplo 401) con cuerpo JSON {"error": mensaje} y cabecera CORS."""
        cuerpo = json.dumps({"error": mensaje}).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self._cabecera_cors()
        self.end_headers()
        self.wfile.write(cuerpo)

    # TITULO ERROR INTERNO

    def _error_interno(self, contexto, error, id_correlacion=None):
        """Registra el detalle de una excepción SOLO en el servidor y responde 500 con un mensaje neutro y un ID de correlación (V04); si la petición ya tenía ID se reutiliza."""
        id_correlacion = id_correlacion or limites.nuevo_id()
        print(f"[servidor] error id={id_correlacion} {contexto}: {type(error).__name__}: {error}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        try:
            self._rechazar(500, limites.mensaje_con_id(limites.MENSAJE_ERROR_INTERNO, id_correlacion))
        except Exception:
            pass
        return id_correlacion

    # TITULO IDENTIFICAR

    def _identificar(self, mutacion=False):
        """Averigua de qué cuenta es la petición y deja `self.path` sin el prefijo `/t/<cuenta>`.

        La dirección puede venir como `/t/demo/ruta` o `/t/real/ruta`. Encendido el multiusuario, devuelve (usuario_id, es_demo) si la cookie de sesión es válida; si no, responde 401
        (sin sesión, sesión cerrada, vencida o por inactividad, o dirección sin cuenta) y devuelve None (quien llama debe terminar). En modo legado (multiusuario apagado) se devuelve
        ("legado",) pero se exige una sesión válida para cualquier mutación (POST). `/salud` es pública.

        La sesión se comprueba contra la base, con una memoria de MEMORIA_SESION_S segundos: cerrar sesión (en este dispositivo, en todos o al cambiar la contraseña) la invalida
        de inmediato. Si no se puede comprobar (la base no responde) las lecturas siguen con el último resultado conocido, pero una petición que modifica (`mutacion=True`) y
        una sesión nunca vista responden 503."""
        analizada = urlparse(self.path)
        partes = analizada.path.split("/")
        cuenta = ""
        if len(partes) >= 3 and partes[1] == "t":
            cuenta = unquote(partes[2])
            self.path = "/" + "/".join(partes[3:]) + (("?" + analizada.query) if analizada.query else "")
        if urlparse(self.path).path.strip("/") == "salud":
            return ("anonimo",)
        # En modo legado, solo se exige sesión para mutaciones (POST); los GET sin sesión se permiten
        if not sesiones_capital.MULTIUSUARIO and not mutacion:
            return ("legado",)
        token = boleto_sesion.leer_cookie(self.headers.get("Cookie", ""))
        if not token or (sesiones_capital.MULTIUSUARIO and cuenta not in ("demo", "real")):
            self._rechazar(401, "no autorizado")
            return None
        resultado = sesion_persistente.consultar(token, memoria_s=MEMORIA_SESION_S)
        usuario = resultado["usuario"]
        if usuario is None:
            if resultado["incierto"]:
                self._rechazar(503, "no se pudo comprobar la sesión")
            else:
                self._rechazar(401, "sesión cerrada")
            return None
        if resultado["incierto"] and mutacion:
            self._rechazar(503, "no se pudo comprobar la sesión")
            return None
        self._sesion_token = token
        return (int(usuario["id"]), cuenta == "demo") if sesiones_capital.MULTIUSUARIO else ("legado",)

    # TITULO COOKIE SEGURA

    def _cookie_segura(self) -> bool:
        """True si la plataforma se sirve por HTTPS (PLATAFORMA_URL con https o el proxy lo indica en X-Forwarded-Proto): entonces la cookie lleva `Secure`."""
        return os.environ.get("PLATAFORMA_URL", "").strip().lower().startswith("https://") or (self.headers.get("X-Forwarded-Proto", "") or "").lower() == "https"

    # TITULO ATENDER SESION

    def _atender_sesion(self, cerrar):
        """`POST /t/sesion` (canjea un boleto por la cookie de sesión) y `POST /t/sesion/cerrar` (la borra).

        Solo desde páginas de la propia plataforma (Origin permitido). El boleto lo emite Streamlit para el usuario ya autenticado: lleva el token de la sesión, vence a los 60 segundos y
        se canjea una sola vez; además la sesión debe seguir vigente en la base. La cookie se emite con HttpOnly, SameSite=Lax y, con HTTPS, Secure, y dura lo que la sesión persistente."""
        if not self._origen_local():
            self._rechazar(403, "origen no permitido")
            return
        try:
            n = int(self.headers.get("Content-Length", 0) or 0)
        except ValueError:
            n = -1
        if n < 0 or n > boleto_sesion.MAX_BOLETO:
            self.close_connection = True
            self._rechazar(413 if n > 0 else 400, limites.MENSAJE_CUERPO_GRANDE if n > 0 else limites.MENSAJE_SOLICITUD_INVALIDA)
            return
        cuerpo = self.rfile.read(n) if n else b""
        if cerrar:
            self._responder({"ok": True}, boleto_sesion.cabecera_set_cookie("", 0, self._cookie_segura()))
            return
        token = boleto_sesion.canjear(cuerpo.decode("utf-8", "replace").strip())
        if not token or sesion_persistente.consultar(token, memoria_s=0)["usuario"] is None:
            self._rechazar(401, "boleto no válido")
            return
        self._responder({"ok": True}, boleto_sesion.cabecera_set_cookie(token, sesion_persistente.DIAS_DURACION * 24 * 3600, self._cookie_segura()))

    # TITULO STREAM

    def _stream(self, simbolos, motor, clave):
        """SSE: envía la foto completa y luego solo los cambios, hasta que el
        navegador cierre la conexión.

        Recibe la lista de símbolos a seguir. Registra la suscripción en el motor, y en bucle
        espera cambios (motor.esperar), envía eventos `data:` con ticks ("t") y cuenta ("acc"),
        o un comentario `: ping` de keep-alive cada PING_SSE segundos. Termina silenciosamente
        cuando el cliente se desconecta.
        """
        # Cabeceras estándar de un flujo Server-Sent Events
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self._cabecera_cors()
        self.end_headers()
        # Suscribe los símbolos para que el motor empiece a leerlos
        motor.suscribir(simbolos)
        # seq = último cambio ya enviado a este cliente
        seq = 0
        ultimo_envio = time.time()
        token_sesion = getattr(self, "_sesion_token", None)     # None con el modo multiusuario apagado y una lectura sin sesión
        ultima_revision = time.time()
        try:
            # Indica al navegador reconectar a los 2 s si se corta
            self.wfile.write(b"retry: 2000\n\n")
            while not motor._detenido:     # si el motor se apagó, se corta: el navegador reconecta y recibe uno nuevo
                # Cada pocos segundos se vuelve a comprobar la sesión: si la persona cerró sesión (o venció por inactividad), se corta la conexión (la reconexión recibe 401)
                if token_sesion is not None and time.time() - ultima_revision >= REVISION_STREAM_S:
                    ultima_revision = time.time()
                    comprobada = sesion_persistente.consultar(token_sesion, memoria_s=MEMORIA_SESION_S)
                    if comprobada["usuario"] is None and not comprobada["incierto"]:
                        self.close_connection = True
                        break
                # Solo lo que cambió desde la última secuencia enviada
                nuevo, ticks, cuenta = motor.foto(simbolos, seq)
                seq = nuevo
                # Hay novedades: las envía; si no, emite ping si pasó mucho tiempo
                if ticks or cuenta:
                    mensaje = {"t": ticks}
                    if cuenta:
                        mensaje["acc"] = cuenta
                    self.wfile.write(b"data: " + json.dumps(mensaje).encode("utf-8") + b"\n\n")
                    self.wfile.flush()
                    ultimo_envio = time.time()
                elif time.time() - ultimo_envio >= PING_SSE:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    ultimo_envio = time.time()
                motor.suscribir(simbolos)          # mantiene viva la suscripción
                motor.esperar(seq, tiempo_espera=PING_SSE)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass   # el navegador cerró la pestaña o cambió de vista

    # TITULO DO GET

    def do_GET(self):
        """Identifica la cuenta de la petición (cookie de sesión y cuenta en la dirección) y atiende el GET con la sesión y el motor de esa cuenta."""
        clave = self._identificar()
        if clave is None:
            return
        if clave != ("anonimo",) and not _FRECUENCIA.permitir(clave, "lectura", limites.LECTURAS_POR_MINUTO):
            self._rechazar(429, limites.MENSAJE_DEMASIADAS)
            return
        with sesiones_capital.con_clave(clave):
            self._atender_get(clave)

    # TITULO ATENDER GET

    def _atender_get(self, clave):
        """Enruta las peticiones GET: /stream, /ticks, /simbolos, /salud, /dom/<s>, /velas/<s> y /ultima/<s>.

        Los errores se devuelven como JSON {"error": ...}; las rutas desconocidas también.
        """
        # Separa ruta (por tramos) y parámetros de consulta; tf por defecto H1
        parsed = urlparse(self.path)
        partes = [unquote(p) for p in parsed.path.strip("/").split("/")]
        qs = parse_qs(parsed.query)
        temporalidad = qs.get("tf", ["H1"])[0]
        try:
            if temporalidad not in limites.TEMPORALIDADES:
                raise limites.ErrorSolicitud("tf: temporalidad no válida")
            if len(partes) >= 2 and partes[0] in ("dom", "velas", "ultima"):
                limites.simbolo_valido(partes[1])
            if partes and partes[0] == "stream":
                if not _STREAMS.entrar(clave, limites.MAX_STREAMS_POR_CUENTA):
                    self._rechazar(429, limites.MENSAJE_DEMASIADAS)
                    return
                try:
                    simbolos = _lista_simbolos(qs)
                    precalentar(simbolos)          # velas de la lista de activos listas en memoria (solo Capital.com)
                    self._stream(simbolos, MOTORES.de(clave), clave)
                finally:
                    _STREAMS.salir(clave)
            elif partes and partes[0] == "ticks":
                simbolos = _lista_simbolos(qs)
                motor = MOTORES.de(clave)
                motor.suscribir(simbolos)
                precalentar(simbolos)
                _, ticks, cuenta = motor.foto(simbolos, 0)
                self._responder({"t": ticks, "acc": cuenta})
            elif partes and partes[0] == "simbolos":
                self._responder(listar_simbolos())
            elif partes and partes[0] == "salud":
                self._responder({"ok": True, "v": VERSION_API})
            elif len(partes) >= 2 and partes[0] == "dom":
                # Nivel 1 del libro (solo Capital.com; MT5 usa su propio libro desde Streamlit)
                from herramientas.puente_mt5 import PROVEEDOR, resolver_simbolo
                if PROVEEDOR == "capital":
                    from .streaming_capital import stream_de
                    self._responder(stream_de(clave).dom(resolver_simbolo(partes[1])))
                else:
                    self._responder({"disponible": False, "motivo": "Solo disponible con Capital.com."})
            elif len(partes) >= 2 and partes[0] == "velas":
                n = max(1, min(int(qs.get("n", ["150"])[0]), limites.MAX_VELAS))
                self._responder(obtener_velas(partes[1], temporalidad, n))
            elif len(partes) >= 2 and partes[0] == "ultima":
                self._responder(obtener_ultima(partes[1], temporalidad))
            else:
                self._responder({"error": "ruta no reconocida"})
        except (limites.ErrorSolicitud, ValueError):
            self._rechazar(400, limites.MENSAJE_SOLICITUD_INVALIDA)
        except Exception as e:
            self._error_interno(f"GET {parsed.path}", e)

    # TITULO ORIGEN LOCAL

    # --- Modificaciones (POST) ----------------------------------------------
    def _origen_local(self) -> bool:
        """Devuelve True si el encabezado Origin pertenece a un host permitido (localhost o SERVIDOR_ORIGENES): autoriza los POST.

        Solo las páginas de la propia plataforma pueden modificar posiciones: otra web abierta en el navegador no puede
        (y en modo multiusuario además hace falta el token del usuario)."""
        host = urlparse(self.headers.get("Origin", "") or "").hostname
        return host in HOSTS_PERMITIDOS

    # TITULO DO OPTIONS

    def do_OPTIONS(self):
        """Responde la verificación previa (preflight) de CORS con 204 y los métodos/cabeceras permitidos."""
        self.send_response(204)
        self._cabecera_cors()
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    # TITULO DO POST

    def do_POST(self):
        """Atiende `POST /t/sesion` y `/t/sesion/cerrar` (la cookie de sesión); el resto identifica la cuenta de la petición (cookie) y atiende el POST con la sesión de esa cuenta."""
        ruta_sesion = urlparse(self.path).path.rstrip("/")
        if ruta_sesion in ("/t/sesion", "/t/sesion/cerrar"):
            self._atender_sesion(ruta_sesion.endswith("/cerrar"))
            return
        clave = self._identificar(mutacion=True)
        if clave is None:
            return
        if not _FRECUENCIA.permitir(clave, "orden", limites.ORDENES_POR_MINUTO):
            limites.auditar(limites.nuevo_id(), limites.texto_actor(clave), urlparse(self.path).path.strip("/"), "rechazada_frecuencia")
            self._rechazar(429, limites.MENSAJE_DEMASIADAS)
            return
        with sesiones_capital.con_clave(clave):
            self._atender_post(clave)

    # TITULO ATENDER POST

    def _atender_post(self, clave):
        """Enruta las órdenes de trading: /sltp, /orden, /orden/modificar, /orden/eliminar y /mercado.

        Rechaza con 403 los orígenes que no sean locales, con 413 los cuerpos mayores que MAX_CUERPO_POST y con 400 los datos que no
        pasan la validación (tipos, rangos, valores finitos), todo ANTES de llamar al bróker. Ejecuta la operación bajo CANDADO_MT5
        mediante herramientas.puente_mt5 y responde con el resultado (o {"error": ...}). Una excepción inesperada devuelve un 500 neutro con
        ID de correlación. Cada orden queda en la auditoría (actor, ruta, operación y resultado, sin cuerpo ni token).
        """
        # Bloquea peticiones de páginas externas (CSRF)
        if not self._origen_local():
            cuerpo = b'{"error": "origen no permitido"}'
            self.send_response(403)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)
            return
        ruta = urlparse(self.path).path.strip("/")
        actor = limites.texto_actor(clave)
        id_correlacion = limites.nuevo_id()
        try:
            # Tamaño declarado del cuerpo: se comprueba antes de leer nada
            try:
                n = int(self.headers.get("Content-Length", 0) or 0)
            except ValueError:
                n = -1
            if n < 0:
                self.close_connection = True
                limites.auditar(id_correlacion, actor, ruta, "rechazada_solicitud")
                self._rechazar(400, limites.mensaje_con_id(limites.MENSAJE_SOLICITUD_INVALIDA, id_correlacion))
                return
            if n > limites.MAX_CUERPO_POST:
                self.close_connection = True           # el cuerpo no se lee: la conexión no se puede reutilizar
                limites.auditar(id_correlacion, actor, ruta, "rechazada_tamano")
                self._rechazar(413, limites.mensaje_con_id(limites.MENSAJE_CUERPO_GRANDE, id_correlacion))
                return
            try:
                datos = limites.validar_orden(ruta, json.loads(self.rfile.read(n) or b"{}"))
            except (limites.ErrorSolicitud, ValueError) as motivo:
                print(f"[servidor] solicitud no válida id={id_correlacion} actor={actor} ruta={ruta}: {motivo}", file=sys.stderr)
                limites.auditar(id_correlacion, actor, ruta, "rechazada_solicitud")
                self._rechazar(400, limites.mensaje_con_id(limites.MENSAJE_SOLICITUD_INVALIDA, id_correlacion))
                return
            with CANDADO_MT5:   # mismo candado que el motor: la API de MT5 no es thread-safe
                if ruta == "sltp":
                    resultado = modificar_sltp(_tk(datos["ticket"]), datos["sl"], datos["tp"])
                elif ruta == "orden":
                    with idempotencia_ordenes.con_clave(datos.get("clave") and f"web:{datos['clave']}"):
                        resultado = colocar_orden_pendiente(datos["symbol"], datos["lado"], datos["volumen"], datos["precio"])
                elif ruta == "orden/modificar":
                    resultado = modificar_orden(_tk(datos["ticket"]), datos["precio"], datos["sl"], datos["tp"], datos["caducidad"], datos["expiracion"])
                elif ruta == "orden/eliminar":
                    resultado = eliminar_orden(_tk(datos["ticket"]))
                else:
                    with idempotencia_ordenes.con_clave(datos.get("clave") and f"web:{datos['clave']}"):
                        resultado = ejecutar_orden_mercado(datos["symbol"], datos["lado"], datos["volumen"])
            limites.auditar(id_correlacion, actor, ruta, "error" if isinstance(resultado, dict) and resultado.get("error") else "ok",
                            datos.get("symbol"), datos.get("lado"), datos.get("volumen"))
            self._responder(resultado)
        except TimeoutError:
            self.close_connection = True
            limites.auditar(id_correlacion, actor, ruta, "rechazada_tiempo")
        except Exception as e:
            limites.auditar(id_correlacion, actor, ruta, "error_interno")
            self._error_interno(f"POST /{ruta} actor={actor}", e, id_correlacion)

    # TITULO LOG MESSAGE

    def log_message(self, *args):
        """Anula el registro de accesos del servidor base para no saturar la consola."""
        pass  # silencia los logs de acceso en consola


# -------------------------------------------------------------------------------------------------------
# ------------------------------------ FIN Piña y Jara manejador .PY ------------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
