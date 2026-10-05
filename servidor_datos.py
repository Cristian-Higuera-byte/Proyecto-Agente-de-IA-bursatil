"""
servidor_datos.py
-----------------
Mini-servidor de datos de MetaTrader 5 para alimentar el dashboard en TIEMPO REAL.

Dos funciones:
  1) Velas para el gráfico (Lightweight Charts): carga inicial + última vela.
  2) MOTOR DE PRECIOS EN VIVO (streaming): un único hilo lee los ticks de MT5
     cada ~250 ms para los símbolos que la página está mostrando y los EMPUJA al
     navegador por Server-Sent Events (SSE). El navegador actualiza los números
     directamente en el DOM, sin reejecutar Streamlit (como las plataformas de
     trading). Así hay UNA sola conexión a MT5 para precios, en vez de varios
     fragmentos `run_every` consultando cada uno por su cuenta.

Cómo ejecutarlo (en una terminal APARTE, además del 'streamlit run app.py'):
    env\\Scripts\\python servidor_datos.py

Endpoints:
    GET /velas/<símbolo>?tf=H1&n=150   -> lista de velas OHLC (carga inicial del gráfico)
    GET /ultima/<símbolo>?tf=H1        -> última vela (resincroniza volumen/vela nueva)
    GET /stream?s=EURUSD...,BTCUSD     -> SSE: ticks en vivo + cuenta (saldo, P/G y P/G por posición)
    GET /ticks?s=EURUSD...,BTCUSD      -> foto instantánea (JSON) de esos ticks
    GET /salud                         -> {"ok": true} (lo usa Streamlit para saber si hay feed)

Nota: usa solo la librería estándar de Python (http.server), no requiere instalar nada.
El terminal de MetaTrader 5 debe estar abierto y logueado.
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

import MetaTrader5 as mt5  # type: ignore[import-untyped]
from tools.mt5_bridge import inicializar_mt5, obtener_datos_historicos, resolver_simbolo

PUERTO = 8000

# Temporalidades soportadas (igual que el selector del dashboard)
TF_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
    "MN1": mt5.TIMEFRAME_MN1,
}

# Todas las llamadas a MT5 de ESTE proceso pasan por aquí (la API no es thread-safe
# y el servidor atiende cada petición en su propio hilo).
_IO = threading.RLock()

INTERVALO_TICKS = 0.25       # s entre lecturas de ticks (4 por segundo)
INTERVALO_CUENTA = 1.0       # s entre lecturas de saldo / P-G
TTL_REFERENCIA = 300         # s que se reutiliza el cierre del día anterior
TTL_SUSCRIPCION = 60         # s sin clientes pidiendo un símbolo -> se deja de leer
PING_SSE = 15                # s sin cambios -> comentario keep-alive


def obtener_velas(simbolo: str, tf: str, n: int) -> list:
    """Devuelve una lista de velas OHLC de MT5 en formato JSON para Lightweight Charts."""
    with _IO:
        inicializar_mt5()
        df = obtener_datos_historicos(simbolo, timeframe=TF_MAP.get(tf, mt5.TIMEFRAME_H1), n_velas=n)
    if df.empty:
        return []
    velas = []
    for tiempo, fila in df.iterrows():
        velas.append({
            "time": int(tiempo.timestamp()),
            "open": round(float(fila["open"]), 5),
            "high": round(float(fila["high"]), 5),
            "low": round(float(fila["low"]), 5),
            "close": round(float(fila["close"]), 5),
            "volume": float(fila["tick_volume"]),
        })
    return velas


# ---------------------------------------------------------------------------
# MOTOR DE PRECIOS EN VIVO
# ---------------------------------------------------------------------------
class MotorPrecios:
    """Lee ticks de MT5 en un solo hilo y guarda la última foto de cada símbolo.
    Los clientes SSE esperan en una Condition y reciben SOLO lo que cambió."""

    def __init__(self):
        self._cond = threading.Condition()
        self._seq = 0                 # contador global de cambios
        self._ticks: dict = {}        # pedido -> {"b","a","l","t","ch","pct","seq"}
        self._cuenta: dict = {}       # {"equity","balance","profit","currency","seq"}
        self._subs: dict = {}         # pedido -> último instante en que un cliente lo pidió
        self._reales: dict = {}       # pedido -> nombre real en el terminal
        self._ref: dict = {}          # real -> (cierre_previo, instante)
        self._ultimo_msc: dict = {}   # real -> time_msc del último tick procesado

    # --- suscripciones -----------------------------------------------------
    def suscribir(self, simbolos):
        ahora = time.time()
        with self._cond:
            for s in simbolos:
                self._subs[s] = ahora

    def _activos(self):
        limite = time.time() - TTL_SUSCRIPCION
        with self._cond:
            for s in [s for s, t in self._subs.items() if t < limite]:
                self._subs.pop(s, None)
            return list(self._subs.keys())

    # --- lecturas de MT5 (solo desde el hilo del motor) -------------------
    def _real(self, pedido):
        real = self._reales.get(pedido)
        if real is None:
            with _IO:
                real = resolver_simbolo(pedido)
                mt5.symbol_select(real, True)
            self._reales[pedido] = real
        return real

    def _cierre_previo(self, real):
        """Cierre de la vela diaria ANTERIOR: base de la variación del día."""
        ref = self._ref.get(real)
        if ref and time.time() - ref[1] < TTL_REFERENCIA:
            return ref[0]
        valor = None
        with _IO:
            rates = mt5.copy_rates_from_pos(real, mt5.TIMEFRAME_D1, 0, 2)
        if rates is not None and len(rates) >= 2:
            valor = float(rates[-2]["close"])
        elif rates is not None and len(rates) == 1:
            valor = float(rates[0]["open"])
        self._ref[real] = (valor, time.time())
        return valor

    def _leer_ticks(self):
        cambios = {}
        for pedido in self._activos():
            try:
                real = self._real(pedido)
                with _IO:
                    tick = mt5.symbol_info_tick(real)
                if tick is None or not (tick.bid or tick.ask):
                    continue
                if self._ultimo_msc.get(real) == tick.time_msc and pedido in self._ticks:
                    continue          # sin tick nuevo -> nada que enviar
                self._ultimo_msc[real] = tick.time_msc
                precio = tick.last if tick.last > 0 else tick.bid
                previo = self._cierre_previo(real)
                ch = (precio - previo) if previo else 0.0
                pct = (ch / previo * 100) if previo else 0.0
                cambios[pedido] = {
                    "b": tick.bid, "a": tick.ask, "l": precio,
                    "t": int(tick.time), "ch": ch, "pct": pct,
                }
            except Exception:
                continue
        return cambios

    def _leer_cuenta(self):
        with _IO:
            info = mt5.account_info()
            posiciones = mt5.positions_get() or []
        if info is None:
            return None
        # P/G neto por posición (profit + swap) → la suma coincide con info.profit
        pos = {str(p.ticket): round(p.profit + p.swap, 2) for p in posiciones}
        pc = {str(p.ticket): p.price_current for p in posiciones}   # precio actual (Inicio)
        return {"equity": info.equity, "balance": info.balance,
                "profit": info.profit, "currency": info.currency,
                "margin": info.margin, "margin_free": info.margin_free,
                "margin_level": info.margin_level, "credit": info.credit,
                # % del equity usado como margen (barra "margen usado" de Inicio)
                "uso_margen": round(info.margin / info.equity * 100, 2) if info.equity else 0.0,
                "pos": pos, "pc": pc}

    # --- bucle principal ---------------------------------------------------
    def correr(self):
        ultima_cuenta = 0.0
        while True:
            inicio = time.time()
            try:
                cambios = self._leer_ticks()
                cuenta = None
                if inicio - ultima_cuenta >= INTERVALO_CUENTA:
                    ultima_cuenta = inicio
                    cuenta = self._leer_cuenta()
                    if cuenta and all(self._cuenta.get(k) == v for k, v in cuenta.items()):
                        cuenta = None   # sin cambios
                if cambios or cuenta:
                    with self._cond:
                        self._seq += 1
                        for k, v in cambios.items():
                            v["seq"] = self._seq
                            self._ticks[k] = v
                        if cuenta:
                            cuenta["seq"] = self._seq
                            self._cuenta = cuenta
                        self._cond.notify_all()
            except Exception as e:
                print(f"[motor] error leyendo MT5: {e}")
                time.sleep(1)
            time.sleep(max(0.0, INTERVALO_TICKS - (time.time() - inicio)))

    # --- lectura para los clientes ----------------------------------------
    def foto(self, simbolos, desde_seq=0):
        """Ticks (de esos símbolos) y cuenta que cambiaron después de `desde_seq`."""
        with self._cond:
            ticks = {s: {k: v for k, v in self._ticks[s].items() if k != "seq"}
                     for s in simbolos
                     if s in self._ticks and self._ticks[s]["seq"] > desde_seq}
            cuenta = None
            if self._cuenta and self._cuenta.get("seq", 0) > desde_seq:
                cuenta = {k: v for k, v in self._cuenta.items() if k != "seq"}
            return self._seq, ticks, cuenta

    def esperar(self, seq, timeout):
        with self._cond:
            self._cond.wait_for(lambda: self._seq > seq, timeout=timeout)
            return self._seq


MOTOR = MotorPrecios()


def _lista_simbolos(qs) -> list:
    crudo = qs.get("s", [""])[0]
    return [s for s in (x.strip() for x in crudo.split(",")) if s][:80]


class Manejador(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _responder(self, obj):
        cuerpo = json.dumps(obj).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Access-Control-Allow-Origin", "*")  # permite el fetch desde el iframe del gráfico
        self.end_headers()
        self.wfile.write(cuerpo)

    def _stream(self, simbolos):
        """SSE: envía la foto completa y luego solo los cambios, hasta que el
        navegador cierre la conexión."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
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
            elif partes and partes[0] == "salud":
                self._responder({"ok": True})
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

    def log_message(self, *args):
        pass  # silencia los logs de acceso en consola


if __name__ == "__main__":
    inicializar_mt5()
    threading.Thread(target=MOTOR.correr, name="motor-precios", daemon=True).start()
    servidor = ThreadingHTTPServer(("127.0.0.1", PUERTO), Manejador)
    servidor.daemon_threads = True
    print(f"Servidor de datos MT5 activo en http://localhost:{PUERTO}  (Ctrl+C para detener)")
    print(f"  · Precios en vivo por SSE cada {int(INTERVALO_TICKS * 1000)} ms  (/stream)")
    servidor.serve_forever()
