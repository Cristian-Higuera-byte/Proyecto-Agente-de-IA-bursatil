# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ------------------------------- INICIO Piña y Jara descarga_segura .PY --------------------------------
# -------------------------------------------------------------------------------------------------------

"""
descarga_segura.py
------------------
Descargas HTTP(S) del servidor hacia internet sin llegar nunca a una red interna (V16 de la auditoría de seguridad).

Las noticias, los logos y los feeds se descargan desde direcciones que salen de fuentes externas. Antes solo se comprobaba el nombre de la primera dirección, una vez y solo en IPv4, y después
`urllib` volvía a resolver el nombre por su cuenta y seguía las redirecciones sin revisarlas: una dirección pública que redirigiera a `127.0.0.1`, a una red privada o al servicio de metadatos
de la nube hacía que el servidor pidiera y procesara una respuesta interna. Aquí se hace distinto:

  - Cada salto se revalida por completo: esquema (solo http y https), sin usuario ni contraseña en la dirección, puerto permitido (80 y 443) y TODAS las direcciones IP del nombre, IPv4 e IPv6.
    Una sola que no sea pública (loopback, redes privadas, enlace local, metadatos, compartidas, reservadas, multicast, NAT64, 6to4, Teredo o una IPv4 incrustada en IPv6) rechaza el destino.
  - Las redirecciones no las sigue el transporte: se leen aquí, una por una, con un máximo de saltos.
  - La conexión se abre contra la IP YA validada, no contra el nombre: un nombre que cambia su resolución entre la comprobación y la conexión (rebinding) no puede llevar a otra dirección.
    Con https el certificado y el nombre de servidor se siguen verificando contra el nombre original.
  - Se limita el tamaño de la respuesta y el tiempo total de lectura.
La política de destino es un filtro de aplicación: en la infraestructura conviene además bloquear la salida hacia redes internas y metadatos con el cortafuegos del servidor.
"""
import http.client
import ipaddress
import socket
import ssl
import time
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

# Puertos a los que se permite conectar: los de la web normal.
PUERTOS_PERMITIDOS = (80, 443)
# Redirecciones que se siguen como máximo.
MAXIMO_REDIRECCIONES = 5
_CODIGOS_REDIRECCION = (301, 302, 303, 307, 308)
_LARGO_MAXIMO_URL = 2048
_BLOQUE_LECTURA = 65536
# Rangos IPv6 que llevan una IPv4 incrustada o que otorgan acceso a otras redes: se rechazan completos.
_REDES_BLOQUEADAS = tuple(ipaddress.ip_network(r) for r in ("64:ff9b::/96", "64:ff9b:1::/48", "2002::/16", "2001::/32", "::/128"))


# TITULO ERROR DESCARGA RECHAZADA

class DescargaRechazada(Exception):
    """Se lanza cuando la política de destino rechaza una dirección: esquema o puerto no permitidos, dirección que no es pública, demasiadas redirecciones o una respuesta demasiado lenta."""


# TITULO RESPUESTA

@dataclass
class Respuesta:
    """Respuesta de una descarga: código HTTP, cabeceras, cuerpo (hasta el máximo pedido) y la dirección final, después de las redirecciones."""
    estado: int
    cabeceras: http.client.HTTPMessage
    cuerpo: bytes
    url_final: str

    @property
    def codificacion(self) -> str | None:
        """Codificación de caracteres que declara la respuesta (por ejemplo `utf-8`), o None."""
        return self.cabeceras.get_content_charset()


# TITULO IP PUBLICA

def ip_publica(ip: str) -> bool:
    """True solo si `ip` (IPv4 o IPv6, como texto) es una dirección pública de internet.

    Falso para loopback, redes privadas, enlace local (incluidos los metadatos de la nube), espacio compartido, reservadas, multicast, sin especificar, las IPv4 incrustadas en IPv6
    (`::ffff:127.0.0.1`, NAT64, 6to4, Teredo) y cualquier texto que no sea una dirección IP."""
    try:
        direccion = ipaddress.ip_address(str(ip).split("%")[0])
    except ValueError:
        return False
    if direccion.version == 6:
        if direccion.ipv4_mapped is not None:
            direccion = direccion.ipv4_mapped
        elif any(direccion in red for red in _REDES_BLOQUEADAS):
            return False
    return direccion.is_global and not direccion.is_multicast


# TITULO VALIDAR DIRECCION

def _validar_direccion(url: str, puertos: tuple) -> tuple:
    """Revisa la forma de la dirección y devuelve (esquema, nombre del servidor, puerto, ruta con consulta). Lanza DescargaRechazada si no es una dirección http(s) aceptable."""
    if not isinstance(url, str) or not url or len(url) > _LARGO_MAXIMO_URL or any(ord(c) <= 32 or ord(c) == 127 for c in url):
        raise DescargaRechazada("dirección no válida")
    partes = urlsplit(url)
    if partes.scheme not in ("http", "https"):
        raise DescargaRechazada("solo se permiten direcciones http y https")
    if "@" in partes.netloc:
        raise DescargaRechazada("la dirección no puede llevar usuario ni contraseña")
    host = partes.hostname
    if not host:
        raise DescargaRechazada("dirección sin servidor")
    try:
        puerto = partes.port or (443 if partes.scheme == "https" else 80)
    except ValueError:
        raise DescargaRechazada("puerto no válido") from None
    if puerto not in puertos:
        raise DescargaRechazada(f"puerto {puerto} no permitido")
    return partes.scheme, host, puerto, (partes.path or "/") + (f"?{partes.query}" if partes.query else "")


# TITULO RESOLVER

def _resolver(host: str, puerto: int) -> list:
    """Direcciones IP (IPv4 e IPv6) del servidor, en el orden en que las entrega el sistema."""
    return [info[4][0] for info in socket.getaddrinfo(host, puerto, type=socket.SOCK_STREAM)]


# TITULO DIRECCIONES AUTORIZADAS

def _direcciones_autorizadas(host: str, puerto: int) -> list:
    """Resuelve el nombre UNA vez y devuelve sus direcciones, solo si TODAS son públicas. Si alguna no lo es, o no se puede resolver, lanza DescargaRechazada.

    Se exigen todas (no solo la primera): un nombre con una dirección pública y otra interna es la forma más simple de saltarse la comprobación."""
    try:
        ips = _resolver(host, puerto)
    except OSError:
        raise DescargaRechazada("no se pudo resolver el servidor") from None
    if not ips:
        raise DescargaRechazada("el servidor no tiene direcciones")
    if not all(ip_publica(ip) for ip in ips):
        raise DescargaRechazada("el servidor no es público")
    return ips


# TITULO ABRIR SOCKET

def _abrir_socket(ips: list, puerto: int, espera: float):
    """Conecta con la primera de las direcciones ya validadas que responda. Nunca vuelve a resolver el nombre."""
    ultimo_error = OSError("sin direcciones")
    for ip in ips:
        try:
            return socket.create_connection((ip, puerto), espera)
        except OSError as e:
            ultimo_error = e
    raise ultimo_error


# TITULO CONEXION HTTP

class _ConexionHttp(http.client.HTTPConnection):
    """Conexión http que se abre contra una IP ya validada (la cabecera Host sigue siendo el nombre original)."""

    def __init__(self, host: str, puerto: int, ips: list, espera: float):
        super().__init__(host, puerto, timeout=espera)
        self._ips = ips

    def connect(self):
        """Abre el socket contra las IP validadas, sin consultar el DNS."""
        self.sock = _abrir_socket(self._ips, self.port, self.timeout)


# TITULO CONEXION HTTPS

class _ConexionHttps(http.client.HTTPSConnection):
    """Conexión https contra una IP ya validada, verificando el certificado y el nombre de servidor del nombre original."""

    def __init__(self, host: str, puerto: int, ips: list, espera: float):
        super().__init__(host, puerto, timeout=espera, context=ssl.create_default_context())
        self._ips = ips

    def connect(self):
        """Abre el socket contra las IP validadas y negocia TLS con el nombre original (SNI y verificación del certificado)."""
        sock = _abrir_socket(self._ips, self.port, self.timeout)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


# TITULO LEER CUERPO

def _leer_cuerpo(respuesta: http.client.HTTPResponse, maximo: int, limite: float) -> bytes:
    """Lee hasta `maximo` bytes de la respuesta; si pasa el instante `limite` (monotónico) lanza DescargaRechazada: una respuesta que llega gota a gota no mantiene ocupado al servidor.

    Usa `read1` (devuelve lo que haya disponible tras una sola lectura) y no `read`, que esperaría a juntar todo el bloque sin volver a mirar el plazo."""
    partes, leidos = [], 0
    while leidos < maximo:
        if time.monotonic() > limite:
            raise DescargaRechazada("la respuesta tardó demasiado")
        trozo = respuesta.read1(min(_BLOQUE_LECTURA, maximo - leidos))
        if not trozo:
            break
        partes.append(trozo)
        leidos += len(trozo)
    return b"".join(partes)


# TITULO ABRIR

def abrir(url: str, metodo: str = "GET", cabeceras: dict | None = None, espera: float = 10, max_bytes: int = 2_500_000, puertos: tuple = PUERTOS_PERMITIDOS,
          max_redirecciones: int = MAXIMO_REDIRECCIONES, plazo_total: float | None = None) -> Respuesta:
    """Descarga `url` (GET o HEAD) aplicando la política de destino en cada salto y devuelve la `Respuesta`, sea cual sea su código HTTP (404, 304...: quien llama decide).

    `espera` son los segundos máximos de cada operación de red; `plazo_total` (por defecto el doble de `espera`) es el tiempo máximo de todo el cuerpo. Lanza `DescargaRechazada` si la
    política rechaza la dirección o alguna redirección, y los errores normales de red (`OSError`, `http.client.HTTPException`, `ssl.SSLError`) si la conexión falla."""
    limite = time.monotonic() + (plazo_total if plazo_total is not None else espera * 2)
    encabezados = {"Accept-Encoding": "identity", "Connection": "close"}
    encabezados.update(cabeceras or {})
    actual = url
    for _ in range(max_redirecciones + 1):
        esquema, host, puerto, ruta = _validar_direccion(actual, puertos)
        conexion = (_ConexionHttps if esquema == "https" else _ConexionHttp)(host, puerto, _direcciones_autorizadas(host, puerto), espera)
        try:
            conexion.request(metodo, ruta, headers=encabezados)
            respuesta = conexion.getresponse()
            if respuesta.status in _CODIGOS_REDIRECCION:
                destino = respuesta.getheader("Location")
                if not destino:
                    raise DescargaRechazada("redirección sin destino")
                actual = urljoin(actual, destino)
                continue
            cuerpo = b"" if metodo == "HEAD" else _leer_cuerpo(respuesta, max_bytes, limite)
            return Respuesta(respuesta.status, respuesta.msg, cuerpo, actual)
        finally:
            conexion.close()
    raise DescargaRechazada("demasiadas redirecciones")


# -------------------------------------------------------------------------------------------------------
# -------------------------------- FIN Piña y Jara descarga_segura .PY ----------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
