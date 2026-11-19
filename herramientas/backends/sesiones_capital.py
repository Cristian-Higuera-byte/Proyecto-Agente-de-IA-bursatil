# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ----------------------------- INICIO Piña y Jara sesiones_capital .PY ---------------------------------
# -------------------------------------------------------------------------------------------------------

"""
sesiones_capital.py
-------------------
Registro de sesiones de Capital.com POR USUARIO Y MODO (demo o real).

`capital_nucleo.py` implementa una sola cuenta con estado de módulo (tokens, cachés, límite de peticiones).
En vez de reescribirlo, aquí se carga una COPIA independiente de ese módulo por cada (usuario, modo): cada copia
tiene sus propias credenciales, su propia sesión, sus cachés y su propio ritmo de peticiones, así que dos usuarios
nunca comparten cuenta, tokens ni lecturas. La fachada `capital.py` enruta cada llamada a la copia del usuario actual.

Cómo se decide el usuario actual (en este orden):
  0. Con `CAPITAL_MULTIUSUARIO` apagado nada de lo siguiente cuenta: siempre se usa la cuenta del .env.
  1. `como_usuario(usuario_id, es_demo)`: contexto explícito, para hilos y procesos de servidor.
  2. El resolvedor registrado con `fijar_resolvedor(fn)`: la aplicación lo usa para leer el usuario y el modo de la
     sesión de Streamlit (funciona también en los fragmentos, que no vuelven a ejecutar el script principal).
  3. Sin usuario: con `CAPITAL_MULTIUSUARIO` apagado usa la cuenta del .env (modo desarrollo de un solo usuario);
     con `CAPITAL_MULTIUSUARIO=true` usa una copia SIN credenciales, que responde "sin conexión". Así un hilo que
     perdió su contexto falla de forma visible en vez de operar con la cuenta de otro.

Las credenciales salen de `credenciales_bolsa` (cifradas en Supabase) y solo viven en memoria dentro de la copia;
nunca se escriben en logs. Se guardan como máximo `CAPITAL_MAX_SESIONES` copias; al pasar el tope se descarta la menos usada.

Credenciales vigentes entre procesos (V18 de la auditoría): cada copia recuerda la VERSIÓN de las credenciales con que se cargó (`credencial_version` de la fila; la base la renueva en cada guardado).
Cuando el usuario reemplaza o quita su API, otro proceso (el servidor de precios, el motor de copias) no se entera por memoria compartida sino comparando versiones: cada `_VIDA_VERIFICACION_S`
segundos para las lecturas y, SIN caché, justo antes de abrir una operación (`motivo_credenciales_no_vigentes`, que llama la política de apertura). Si la versión cambió o la cuenta ya no existe, la
copia vieja se descarta (y se cierra su sesión en Capital.com); si no se puede verificar, las lecturas siguen con lo que hay pero NO se abren operaciones nuevas (cerrar sigue permitido). La sesión que las
copias comparten por archivo va cifrada, con permisos solo del propietario y marcada con esa versión.
"""
import contextlib
import contextvars
import hashlib
import importlib.util
import os
import threading
import time
from collections import OrderedDict
from typing import Callable, Optional

from dotenv import load_dotenv

load_dotenv()

# Carpeta raíz del proyecto y ruta del núcleo que se copia por usuario
_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_RUTA_NUCLEO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capital_nucleo.py")
# Carpeta de los archivos de sesión compartidos entre procesos (uno por usuario y modo)
_CARPETA_SESIONES = os.path.join(_RAIZ, "data", "sesiones_capital")

# Direcciones de la API de Capital.com para cada modo
_URL_DEMO = "https://demo-api-capital.backend-capital.com/api/v1"
_URL_REAL = "https://api-capital.backend-capital.com/api/v1"

# Con True cada usuario usa sus propias credenciales; con False toda la plataforma usa la cuenta del .env
MULTIUSUARIO = os.getenv("CAPITAL_MULTIUSUARIO", "").strip().lower() in ("true", "1", "si", "sí")
# Máximo de copias de sesión en memoria
_MAX_SESIONES = max(2, int(os.getenv("CAPITAL_MAX_SESIONES", "200") or 200))
# Segundos que se recuerda que un usuario no tiene credenciales (para no consultar Supabase en cada llamada)
_VIDA_SIN_CREDENCIALES_S = 30.0

# Cada cuántos segundos se vuelve a comprobar que las credenciales de una copia que ya está en memoria siguen siendo las vigentes (misma versión). Así, cuando el usuario reemplaza o quita su API, la
# cuenta deja de usar las anteriores también en el servidor de precios (otro proceso, que no se entera de lo que se hace en la pantalla) en menos de este tiempo. Con la base caída se reintenta antes.
_VIDA_VERIFICACION_S = 10.0
_REINTENTO_VERIFICACION_S = 5.0

# Claves especiales del registro
_CLAVE_LEGADO = ("legado",)
_CLAVE_ANONIMO = ("anonimo",)

_CANDADO = threading.RLock()
# clave -> módulo copiado; el orden de la lista es el de uso reciente (el primero es el menos usado)
_copias: "OrderedDict[tuple, object]" = OrderedDict()
# clave -> epoch hasta el que se da por buena la ausencia de credenciales
_sin_credenciales: dict = {}
# clave -> epoch hasta el que no hace falta volver a comprobar que las credenciales siguen guardadas
_verificada_hasta: dict = {}
# Número de copia, para darle a cada módulo un nombre único
_contador = 0
# True cuando ya se borraron los archivos de sesión antiguos (sin cifrar) de la carpeta compartida
_barrido_hecho = False
# Límite de peticiones por segundo que se aplica a cada copia nueva (None = el del núcleo)
_limite_peticiones: Optional[int] = None

# Usuario explícito del hilo actual: (usuario_id, es_demo) o None
_usuario_explicito: contextvars.ContextVar = contextvars.ContextVar("usuario_capital", default=None)
# Función que devuelve (usuario_id, es_demo) del usuario de la sesión actual, o None si no hay
_resolvedor: Optional[Callable[[], Optional[tuple]]] = None


# TITULO FIJAR RESOLVEDOR

def fijar_resolvedor(funcion: Optional[Callable[[], Optional[tuple]]]) -> None:
    """Registra la función que dice quién es el usuario actual: debe devolver (usuario_id, es_demo) o None."""
    global _resolvedor
    _resolvedor = funcion


# TITULO COMO USUARIO

@contextlib.contextmanager
def como_usuario(usuario_id: int, es_demo: bool):
    """Bloque `with` que fija el usuario y el modo para todo lo que se ejecute dentro, en este hilo.

    Es lo que usan los procesos de servidor (motor de órdenes, streaming) que atienden a varios usuarios."""
    marca = _usuario_explicito.set((int(usuario_id), bool(es_demo)))
    try:
        yield
    finally:
        _usuario_explicito.reset(marca)


# TITULO CON CLAVE

@contextlib.contextmanager
def con_clave(clave: tuple):
    """Bloque `with` que fija una clave del registro cualquiera (usuario y modo, o una clave especial) en este hilo.

    Es lo que usa `herramientas/hilos.py` para que un hilo nuevo siga atendiendo al mismo usuario que lo lanzó."""
    marca = _usuario_explicito.set(tuple(clave))
    try:
        yield
    finally:
        _usuario_explicito.reset(marca)


# TITULO CLAVE ACTUAL

def clave_actual() -> tuple:
    """Devuelve la clave del registro del usuario actual: (usuario_id, es_demo), o una clave especial si no hay usuario."""
    if not MULTIUSUARIO:
        return _CLAVE_LEGADO       # modo de un solo usuario: siempre la cuenta del .env, sin importar quién entró
    explicito = _usuario_explicito.get()
    if explicito is not None:
        return explicito
    if _resolvedor is not None:
        try:
            resuelto = _resolvedor()
        except Exception:
            resuelto = None
        if resuelto:
            return (int(resuelto[0]), bool(resuelto[1]))
    return _CLAVE_ANONIMO


# TITULO RUTA DE SESION

def _ruta_sesion(clave: tuple) -> str:
    """Archivo donde la copia comparte su sesión con otros procesos; uno distinto por usuario y modo."""
    huella = hashlib.sha256(repr(clave).encode()).hexdigest()[:16]
    return os.path.join(_CARPETA_SESIONES, f"{huella}.json")


# TITULO FIJAR LIMITE DE PETICIONES

def fijar_limite_peticiones(por_segundo: int) -> None:
    """Cambia el máximo de peticiones por segundo de ESTE proceso para todas las copias, las actuales y las futuras.

    El servidor de datos lo baja a 4 para que, sumado al panel (6), no se supere el tope de 10 por segundo que
    Capital.com aplica a cada cuenta."""
    global _limite_peticiones
    _limite_peticiones = max(1, int(por_segundo))
    with _CANDADO:
        for modulo in _copias.values():
            modulo.fijar_limite_peticiones(_limite_peticiones)


# TITULO CARGAR COPIA

def _cargar_copia(clave: tuple, credenciales: Optional[dict]):
    """Carga una copia nueva e independiente de `capital_nucleo.py` y le pone las credenciales indicadas.

    `credenciales` es {identificador, api_key, api_contrasena, es_demo} o None para una copia SIN cuenta (responde
    "sin conexión"). La clave LEGADO conserva lo que el núcleo leyó del .env. Devuelve el módulo."""
    global _contador
    _contador += 1
    especificacion = importlib.util.spec_from_file_location(f"herramientas.backends.capital_nucleo_{_contador}", _RUTA_NUCLEO)
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    if _limite_peticiones is not None:
        modulo.fijar_limite_peticiones(_limite_peticiones)
    if clave == _CLAVE_LEGADO:
        return modulo
    es_demo = bool(credenciales["es_demo"]) if credenciales else True
    modulo._API_KEY = (credenciales or {}).get("api_key", "")
    modulo._IDENTIFIER = (credenciales or {}).get("identificador", "")
    modulo._API_CONTRASENA = (credenciales or {}).get("api_contrasena", "")
    modulo._ES_DEMO = es_demo
    modulo.BASE = _URL_DEMO if es_demo else _URL_REAL
    modulo._ARCHIVO_SESION = _ruta_sesion(clave)
    modulo._ARCHIVO_CANDADO = modulo._ARCHIVO_SESION + ".lock"
    modulo._CLAVE_REGISTRO = clave
    modulo._VERSION_CREDENCIALES = (credenciales or {}).get("version")
    modulo._VERIFICAR_CREDENCIALES = bool(credenciales)      # una copia con cuenta de usuario verifica su versión con la base antes de abrir
    _barrer_sesiones_antiguas()
    return modulo


# TITULO LEER CREDENCIALES

def _leer_credenciales(clave: tuple) -> Optional[dict]:
    """Lee y descifra las credenciales del usuario y modo de `clave`; None si no hay o no se pudieron leer.

    Nunca escribe secretos en logs: si falla, solo informa el tipo de error."""
    try:
        from herramientas import credenciales_bolsa
        return credenciales_bolsa.obtener_credenciales(clave[0], clave[1])
    except Exception as error:
        print(f"[CAPITAL] No se pudieron leer las credenciales del usuario {clave[0]} ({type(error).__name__}).")
        return None


# TITULO ESTADO DE LAS CREDENCIALES

def _estado_credenciales(clave: tuple) -> tuple:
    """("ok", versión), ("ausente", None) o ("error", None) para las credenciales de `clave` en la base; nunca lanza."""
    try:
        from herramientas import credenciales_bolsa
        return credenciales_bolsa.version_credenciales(clave[0], clave[1])
    except Exception:
        return ("error", None)


# TITULO CERRAR EN SEGUNDO PLANO

def _cerrar_en_segundo_plano(modulo) -> None:
    """Cierra en Capital.com la sesión de una copia que se descarta (y borra su archivo compartido), sin hacer esperar a quien llama. Es de mejor esfuerzo: si falla, la sesión caduca sola."""
    if modulo is None or getattr(modulo, "_CLAVE_REGISTRO", None) is None:
        return
    threading.Thread(target=getattr(modulo, "cerrar_mt5", lambda: None), daemon=True, name="cerrar-sesion-capital").start()


# TITULO RETIRAR COPIA

def _retirar_copia(clave: tuple) -> None:
    """Descarta la copia de `clave` (sus credenciales en memoria y su sesión). Se llama con el candado del registro tomado."""
    modulo = _copias.pop(clave, None)
    _verificada_hasta.pop(clave, None)
    _cerrar_en_segundo_plano(modulo)


# TITULO BARRER SESIONES ANTIGUAS

def _barrer_sesiones_antiguas() -> None:
    """Una sola vez por proceso: borra de la carpeta compartida los archivos de sesión que quedaron en claro (de antes de V18); los nuevos van cifrados."""
    global _barrido_hecho
    if _barrido_hecho:
        return
    _barrido_hecho = True
    try:
        nombres = os.listdir(_CARPETA_SESIONES)
    except OSError:
        return
    for nombre in nombres:
        ruta = os.path.join(_CARPETA_SESIONES, nombre)
        try:
            if not (nombre.endswith(".json") and os.path.isfile(ruta)):
                continue
            with open(ruta, "r", encoding="utf-8", errors="ignore") as fh:
                inicio = fh.read(4)
            if inicio != "pj1:":          # se borra con el archivo ya cerrado (en Windows no se puede borrar uno abierto)
                os.remove(ruta)
        except OSError:
            continue


# TITULO MOTIVO CREDENCIALES NO VIGENTES

def motivo_credenciales_no_vigentes(clave, version) -> str | None:
    """Texto con el motivo por el que NO se debe abrir una operación con una copia cargada con `version`, o None si sus credenciales siguen siendo las vigentes.

    Consulta la base SIN caché (es la verificación previa a una orden nueva, la política de apertura). Rechaza si el usuario quitó la cuenta, si la reemplazó (la versión cambió: descarta la copia vieja
    para que la próxima llamada cargue las nuevas) o si la base no responde y por tanto no se puede comprobar. No aplica a la cuenta del .env ni a las copias sin cuenta."""
    if clave is None or clave in (_CLAVE_LEGADO, _CLAVE_ANONIMO):
        return None
    estado, actual = _estado_credenciales(tuple(clave))
    if estado == "ok" and actual == version:
        return None
    if estado == "error":
        return ("No se pudo verificar la cuenta conectada (la base de datos no responde): por seguridad no se abren operaciones nuevas hasta poder comprobarla. "
                "Cerrar posiciones y mover SL/TP sigue disponible.")
    with _CANDADO:
        modulo = _copias.get(tuple(clave))
        if modulo is not None and getattr(modulo, "_VERSION_CREDENCIALES", None) != actual:
            _retirar_copia(tuple(clave))
        if estado == "ausente":
            _sin_credenciales[tuple(clave)] = time.time() + _VIDA_SIN_CREDENCIALES_S
    if estado == "ausente":
        return "Esta cuenta ya no está conectada: no se pueden abrir operaciones con ella."
    return "Las credenciales de esta cuenta cambiaron: vuelve a intentarlo en un momento."


# TITULO MODULO DE UNA CLAVE

def modulo_de(clave: tuple):
    """Devuelve la copia del núcleo que corresponde a la clave (usuario_id, es_demo), creándola si hace falta.

    Si el usuario no tiene credenciales guardadas para ese modo, devuelve la copia sin cuenta. Es seguro
    llamarla desde varios hilos a la vez. Quien guarde la copia (por ejemplo un stream) debe pedirla de nuevo si
    el usuario cambia sus credenciales."""
    with _CANDADO:
        modulo = _copias.get(clave)
        if modulo is not None and clave not in (_CLAVE_LEGADO, _CLAVE_ANONIMO) and time.time() >= _verificada_hasta.get(clave, 0.0):
            estado, version = _estado_credenciales(clave)
            if estado == "ok" and version == getattr(modulo, "_VERSION_CREDENCIALES", None):
                _verificada_hasta[clave] = time.time() + _VIDA_VERIFICACION_S
            elif estado == "error":
                # La base no responde: las lecturas siguen con lo que hay (una falla pasajera no corta la cuenta); las órdenes nuevas se verifican aparte y se rechazan mientras no se pueda comprobar
                _verificada_hasta[clave] = time.time() + _REINTENTO_VERIFICACION_S
            else:
                # El usuario quitó su API o la reemplazó: la copia (con las credenciales anteriores en memoria) se descarta
                _retirar_copia(clave)
                if estado == "ausente":
                    _sin_credenciales[clave] = time.time() + _VIDA_SIN_CREDENCIALES_S
                    return _modulo_sin_cuenta()
                modulo = None      # reemplazó: más abajo se cargan las nuevas
        if modulo is not None:
            _copias.move_to_end(clave)
            return modulo
        if clave not in (_CLAVE_LEGADO, _CLAVE_ANONIMO) and time.time() < _sin_credenciales.get(clave, 0.0):
            return _modulo_sin_cuenta()
        credenciales = None
        if clave not in (_CLAVE_LEGADO, _CLAVE_ANONIMO):
            credenciales = _leer_credenciales(clave)
            if credenciales is None:
                _sin_credenciales[clave] = time.time() + _VIDA_SIN_CREDENCIALES_S
                return _modulo_sin_cuenta()
        modulo = _cargar_copia(clave, credenciales)
        _copias[clave] = modulo
        if clave not in (_CLAVE_LEGADO, _CLAVE_ANONIMO):
            _verificada_hasta[clave] = time.time() + _VIDA_VERIFICACION_S     # acaba de leerse de la base: no hace falta volver a preguntar de inmediato
        _descartar_sobrantes()
        return modulo


# TITULO MODULO ACTUAL

def modulo_actual():
    """Devuelve la copia del núcleo que corresponde al usuario actual (ver `clave_actual`)."""
    return modulo_de(clave_actual())


# TITULO MODULO SIN CUENTA

def _modulo_sin_cuenta():
    """Copia sin credenciales, compartida por todos los que no tienen cuenta conectada; responde "sin conexión".

    Se llama con el candado del registro tomado."""
    modulo = _copias.get(_CLAVE_ANONIMO)
    if modulo is None:
        modulo = _cargar_copia(_CLAVE_ANONIMO, None)
        _copias[_CLAVE_ANONIMO] = modulo
    return modulo


# TITULO DESCARTAR SOBRANTES

def _descartar_sobrantes() -> None:
    """Si hay más copias que el máximo permitido, descarta las menos usadas (nunca la del .env ni la sin cuenta)."""
    for clave in list(_copias):
        if len(_copias) <= _MAX_SESIONES:
            return
        if clave not in (_CLAVE_LEGADO, _CLAVE_ANONIMO):
            _copias.pop(clave, None)


# TITULO PROBAR CREDENCIALES

def probar_credenciales(identificador: str, api_key: str, api_contrasena: str, es_demo: bool) -> dict:
    """Comprueba contra Capital.com que las credenciales sirven, SIN guardarlas ni tocar ninguna sesión de usuario.

    Abre una sesión de prueba (POST /session) y la cierra enseguida. Devuelve {"ok": bool, "mensaje": str} con un
    texto apto para mostrar al usuario; nunca incluye ni registra los secretos."""
    import requests
    base = _URL_DEMO if es_demo else _URL_REAL
    try:
        respuesta = requests.post(
            f"{base}/session",
            headers={"X-CAP-API-KEY": api_key, "Content-Type": "application/json"},
            json={"identifier": identificador, "password": api_contrasena, "encryptedPassword": False},
            timeout=15,
        )
    except requests.exceptions.RequestException:
        return {"ok": False, "mensaje": "No se pudo contactar a Capital.com. Revisa tu conexión e inténtalo de nuevo."}
    if respuesta.status_code == 429:
        return {"ok": False, "mensaje": "Capital.com pidió esperar un poco entre intentos. Prueba otra vez en un minuto."}
    if respuesta.status_code != 200:
        modo = "demo" if es_demo else "real"
        return {"ok": False, "mensaje": f"Capital.com rechazó los datos para la cuenta {modo}. Revisa el correo, la API key "
                                        "y la contraseña de la key, y que la key pertenezca a ese tipo de cuenta."}
    try:
        requests.delete(f"{base}/session", headers={"CST": respuesta.headers.get("CST", ""),
                                                    "X-SECURITY-TOKEN": respuesta.headers.get("X-SECURITY-TOKEN", "")},
                        timeout=10)
    except requests.exceptions.RequestException:
        pass
    return {"ok": True, "mensaje": "Conexión verificada."}


# TITULO PROBAR AMBAS CUENTAS

def probar_ambas_cuentas(identificador: str, api_key: str, api_contrasena: str) -> dict:
    """Prueba los mismos datos contra la cuenta demo y contra la real de Capital.com.

    Devuelve {"demo": {"ok", "mensaje"}, "real": {"ok", "mensaje"}}. Capital permite una sesión nueva por segundo,
    así que entre una prueba y la otra hay una pausa. No guarda nada."""
    demo = probar_credenciales(identificador, api_key, api_contrasena, True)
    time.sleep(1.2)
    real = probar_credenciales(identificador, api_key, api_contrasena, False)
    return {"demo": demo, "real": real}


# TITULO OLVIDAR USUARIO

def olvidar_usuario(usuario_id: int) -> None:
    """Descarta las copias del usuario (demo y real), para que la próxima llamada relea sus credenciales.

    Se usa al guardar, cambiar o borrar las credenciales de un usuario o al cerrar su sesión."""
    with _CANDADO:
        for es_demo in (True, False):
            clave = (int(usuario_id), es_demo)
            _retirar_copia(clave)
            _sin_credenciales.pop(clave, None)
            try:
                os.remove(_ruta_sesion(clave))        # la sesión compartida con otros procesos deja de existir
            except OSError:
                pass


# -------------------------------------------------------------------------------------------------------
# ----------------------------- FIN Piña y Jara sesiones_capital .PY ------------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
