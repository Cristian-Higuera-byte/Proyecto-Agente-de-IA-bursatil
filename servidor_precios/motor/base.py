"""Núcleo del motor: suscripciones, lectura de ticks y cuenta, bucle principal y lectura para los clientes."""
import threading
import time

from proveedores.selector_mt5 import mt5  # type: ignore[import-untyped]
from herramientas import almacen_capital, almacen_oco, almacen_stop_dinamico
from herramientas.puente_mt5 import resolver_simbolo

from ..constantes import (CANDADO_MT5, INTERVALO_CUENTA, INTERVALO_EQUITY, INTERVALO_TICKS,
                          TTL_REFERENCIA, TTL_SUSCRIPCION)
from .oco import MixinOco
from .stop_dinamico import MixinStopDinamico


class MotorPrecios(MixinStopDinamico, MixinOco):
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
        self._trailing: dict = {}     # ticket(int) -> {"dist","paso"} (Stop dinámico)
        self._trailing_mtime = -1.0   # mtime de data/trailing.json ya cargado
        self._oco: dict = {}          # par_id -> {"a","b","symbol","ts"} (OCO)
        self._oco_mtime = -1.0        # mtime de data/oco.json ya cargado
        self._oco_armados: set = set()  # par_id cuyas DOS patas ya se vieron vivas (anti-carrera)

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
            with CANDADO_MT5:
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
        with CANDADO_MT5:
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
                with CANDADO_MT5:
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
        with CANDADO_MT5:
            info = mt5.account_info()
            posiciones = mt5.positions_get() or []
            ordenes = mt5.orders_get() or []          # órdenes pendientes
        if info is None:
            return None
        # P/G neto por posición (profit + swap) → la suma coincide con info.profit
        pos = {str(p.ticket): round(p.profit + p.swap, 2) for p in posiciones}
        pc = {str(p.ticket): p.price_current for p in posiciones}   # precio actual (Inicio)
        # detalle por posición para las líneas del gráfico: símbolo, tipo, lotes, apertura,
        # SL/TP, k = valor de 1 unidad de precio por lote (P/G proyectado) y sm = distancia
        # mínima de SL/TP al precio que exige el bróker
        pi = {}
        specs = {}
        def _spec(simbolo):
            if simbolo not in specs:
                with CANDADO_MT5:
                    si = mt5.symbol_info(simbolo)
                ts = float(getattr(si, "trade_tick_size", 0) or 0)
                specs[simbolo] = (
                    (float(si.trade_tick_value) / ts) if si and ts else 0.0,
                    float(getattr(si, "trade_stops_level", 0) or 0) * float(getattr(si, "point", 0) or 0),
                )
            return specs[simbolo]
        tr = almacen_stop_dinamico.leer()      # tickets con stop dinámico activo (etiqueta "auto")
        for p in posiciones:
            k, sm = _spec(p.symbol)
            pi[str(p.ticket)] = {"s": p.symbol, "t": int(p.type), "v": p.volume, "po": p.price_open,
                                 "sl": p.sl, "tp": p.tp, "k": k, "sm": sm,
                                 "tr": 1 if p.ticket in tr else 0}
        # órdenes pendientes (t: 2 Buy Limit, 3 Sell Limit, 4 Buy Stop, 5 Sell Stop)
        oco_tks = almacen_oco.tickets_en_oco()   # tickets vinculados en un par OCO (etiqueta "OCO")
        orden = {}
        for o in ordenes:
            if int(o.type) not in (2, 3, 4, 5):
                continue
            k, sm = _spec(o.symbol)
            orden[str(o.ticket)] = {"s": o.symbol, "t": int(o.type), "v": o.volume_current,
                                    "po": o.price_open, "sl": o.sl, "tp": o.tp, "k": k, "sm": sm,
                                    # caducidad: 0 GTC, 1 DAY, 2 fecha (ex, hora del servidor)
                                    "tt": int(o.type_time), "ex": int(o.time_expiration or 0),
                                    "oco": 1 if o.ticket in oco_tks else 0}
        return {"equity": info.equity, "balance": info.balance,
                "profit": info.profit, "currency": info.currency,
                "margin": info.margin, "margin_free": info.margin_free,
                "margin_level": info.margin_level, "credit": info.credit,
                # % del equity usado como margen (barra "margen usado" de Inicio)
                "uso_margen": round(info.margin / info.equity * 100, 2) if info.equity else 0.0,
                "pos": pos, "pc": pc, "pi": pi, "ord": orden}


    def _paso_equity_log(self):
        """Guarda un snapshot del equity/balance cada INTERVALO_EQUITY segundos.
        El almacen_capital aplica su propio mínimo entre escrituras, así que llamar
        cada ciclo es inofensivo. Alimenta el drawdown de EQUITY real (el que
        incluye el flotante de posiciones abiertas), que MT5 no guarda por sí solo.
        Ver herramientas/almacen_capital.py para la nota de escalado a multiusuario/Supabase."""
        c = self._cuenta
        eq = c.get("equity")
        if eq is None:
            return
        try:
            almacen_capital.registrar(eq, c.get("balance", eq), min_intervalo=INTERVALO_EQUITY)
        except Exception as e:
            print(f"[motor] no se pudo registrar equity: {e}")

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
                self._paso_trailing()          # mueve los stops dinámicos activos
                self._paso_oco()               # cancela la pata sobrante de los OCO ejecutados
                self._paso_equity_log()        # snapshot de equity (drawdown real, Tanda 2)
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
