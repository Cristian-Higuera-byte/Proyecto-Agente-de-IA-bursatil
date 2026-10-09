"""
posiciones_grafico.py
---------------------
Trading desde el gráfico (como MT5 / XM). Términos de trading en INGLÉS.

- POSICIONES abiertas del símbolo: línea en el precio de apertura con etiqueta
  [lotes con signo | P/G en vivo | ✕]; la ✕ abre el modal de cierre de Cartera.
- ÓRDENES PENDIENTES (Buy/Sell Limit/Stop): línea punteada con etiqueta
  [BUY LIMIT 0.01 | at 1.11982 | ✕]. Se ARRASTRA para cambiar el precio de entrada
  (el número del eje se ajusta mientras se mueve); la ✕ cancela la orden.
- TAKE PROFIT / STOP LOSS de posiciones y órdenes: insignias "TP"/"SL" que se
  arrastran para crear el nivel (con el P/G proyectado a ese precio); los niveles
  existentes son líneas propias que se mueven o se quitan con su ✕.
- MENÚ DEL CLIC DERECHO: en el precio del cursor ofrece Buy Limit / Sell Stop
  (bajo el mercado) o Sell Limit / Buy Stop (sobre el mercado) con el volumen del
  ticket, y el interruptor One-Click Trading.
- ONE-CLICK TRADING (interruptor del ticket, `ord_oc`; components/one_click.py):
  activo → todo se envía al instante; apagado → cada acción pide confirmar en el
  propio gráfico.

Antes de enviar se valida el lado correcto y la distancia mínima del bróker.
Los envíos van a servidor_datos.py (POST /sltp, /orden, /orden/modificar,
/orden/eliminar; solo desde páginas de localhost), sin rerun de Streamlit.

Piezas:
- `js_posiciones(simbolo)`: JS que central_panel.py inserta DENTRO de `iniciar()`
  del gráfico (usa `chart`, `serie`, `containerEl`, `API`, `DIGITS`, `SIMBOLO`).
  Datos iniciales desde Python; luego en vivo con el mensaje de cuenta del feed
  (`acc.pi` posiciones, `acc.ord` órdenes, `acc.pos` P/G, `acc.pc` precio actual)
  y los ticks (Bid/Ask) que llegan por BroadcastChannel('pj-ticks').
- `gatillos_cierre()`: botones invisibles `chcls_<ticket>` que pulsa la ✕ de una
  posición → abre el modal de cierre en Python.
"""
import json
import time

import streamlit as st
import MetaTrader5 as mt5  # type: ignore[import-untyped]

from tools.mt5_bridge import MT5_LOCK, inicializar_mt5, obtener_posiciones, resolver_simbolo
from tools import trailing_store, oco_store
from components.live_feed import intervalo


def _neto(p: dict) -> float:
    return round(float(p.get("profit", 0) or 0) + float(p.get("swap", 0) or 0), 2)


def _iniciales(real: str) -> dict:
    """Posiciones y órdenes del símbolo con el mismo formato que el feed
    (`acc.pi` / `acc.ord`), más volumen mínimo, distancia mínima y desfase horario.
    OJO: solo datos ESTABLES. Si algo cambiara a cada segundo (Bid/Ask, P/G), el
    HTML del gráfico sería distinto en cada rerun y Streamlit recargaría el iframe
    (se perdería el zoom). Bid/Ask y P/G llegan en vivo por el feed."""
    out = {"pos": {}, "ord": {}, "ba": [0, 0], "vmin": 0.01, "sm": 0.0, "k": 0.0, "off": 0, "em": 0}
    try:
        if not inicializar_mt5():
            return out
        with MT5_LOCK:
            mt5.symbol_select(real, True)
            posiciones = mt5.positions_get(symbol=real) or []
            ordenes = mt5.orders_get(symbol=real) or []
            si = mt5.symbol_info(real)
            tick = mt5.symbol_info_tick(real)
        ts = float(getattr(si, "trade_tick_size", 0) or 0)
        k = (float(si.trade_tick_value) / ts) if si and ts else 0.0
        sm = float(getattr(si, "trade_stops_level", 0) or 0) * float(getattr(si, "point", 0) or 0)
        out.update(sm=sm, k=k, vmin=float(getattr(si, "volume_min", 0.01) or 0.01),
                   em=int(getattr(si, "expiration_mode", 0) or 0))   # 1 GTC · 2 DAY · 4 fecha
        if tick is not None:
            # hora del servidor del bróker − hora real (s), redondeado a 15 min: caducidad por fecha
            out["off"] = round((int(tick.time) - time.time()) / 900) * 900
        tr = trailing_store.leer()      # tickets con stop dinámico activo
        oco_tks = oco_store.tickets_en_oco()   # tickets vinculados en un par OCO
        for p in posiciones:
            out["pos"][str(p.ticket)] = {
                "s": p.symbol, "t": int(p.type), "v": p.volume, "po": p.price_open,
                "sl": p.sl, "tp": p.tp, "k": k, "sm": sm,
                "tr": 1 if p.ticket in tr else 0,
            }
        for o in ordenes:
            if int(o.type) in (2, 3, 4, 5):
                out["ord"][str(o.ticket)] = {
                    "s": o.symbol, "t": int(o.type), "v": o.volume_current, "po": o.price_open,
                    "sl": o.sl, "tp": o.tp, "k": k, "sm": sm,
                    "tt": int(o.type_time), "ex": int(o.time_expiration or 0),
                    "oco": 1 if o.ticket in oco_tks else 0,
                }
    except Exception:
        pass
    return out


_JS = r"""
    // ===== Trading desde el gráfico (components/posiciones_grafico.py) =====
    (function(){
      var REAL = __POS_REAL__, INI = __POS_INI__;
      var POS = INI.pos || {}, ORD = INI.ord || {};
      var BID = INI.ba[0], ASK = INI.ba[1], VMIN = INI.vmin || 0.01, SM = INI.sm || 0, K = INI.k || 0;
      var OFF = INI.off || 0, EM = INI.em || 0;   // desfase hora servidor (s) y modos de caducidad
      var COMPRA = '#3fb950', VENTA = '#f85149', C_TP = '#3fb950', C_SL = '#ff8f00';
      var SEP = 56;   // px entre las etiquetas y el eje de precios (como XM)
      var NOMBRE = {tp: 'Take Profit', sl: 'Stop Loss'};
      var TIPO = {0: 'Buy', 1: 'Sell', 2: 'Buy Limit', 3: 'Sell Limit', 4: 'Buy Stop', 5: 'Sell Stop'};
      var PD = window.parent.document;

      var est = document.createElement('style');
      est.textContent =
        '#pj-pos{position:absolute;pointer-events:none;z-index:6;overflow:hidden;}' +
        '#pj-pos .pl{position:absolute;left:0;height:0;}' +
        '#pj-pos .ln{position:absolute;left:0;top:0;height:0;border-top:1px solid;}' +
        '#pj-pos .po .ln{border-top-style:dashed;}' +
        '#pj-pos .tg{position:absolute;top:-11px;height:22px;display:flex;align-items:stretch;pointer-events:auto;' +
        'font:600 12px "Source Sans Pro",system-ui,sans-serif;border-radius:4px;overflow:hidden;' +
        'box-shadow:0 2px 8px rgba(0,0,0,.45);cursor:default;white-space:nowrap;}' +
        '#pj-pos .lv .tg,#pj-pos .po .tg{cursor:ns-resize;}' +
        '#pj-pos .vo{display:flex;align-items:center;padding:0 8px;color:#fff;border:1px solid transparent;border-right:none;}' +
        '#pj-pos .pg{display:flex;align-items:center;padding:0 9px;background:#161b22;border:1px solid;border-left:none;border-right:none;' +
        'font-family:ui-monospace,Consolas,monospace;font-variant-numeric:tabular-nums;}' +
        '#pj-pos .x{display:flex;align-items:center;justify-content:center;width:22px;background:#161b22;border:1px solid;' +
        'border-left:1px solid #30363d;color:#8b949e;cursor:pointer;font-size:13px;}' +
        '#pj-pos .x:hover{background:#da3633;color:#fff;}' +
        '#pj-pos .ej{position:absolute;right:0;top:-10px;height:20px;display:flex;align-items:center;justify-content:center;' +
        'box-sizing:border-box;color:#fff;font:600 11.5px ui-monospace,Consolas,monospace;}' +   // todos iguales, rectángulo completo
        '#pj-pos .ejlive{position:absolute;right:0;z-index:7;background:#e6edf3;color:#0d1117;}' +   // precio en vivo (blanco), lo dibujamos nosotros
        '#pj-pos .pl.pend{opacity:.5;}' +
        '#pj-pos .pl.mal .ln{border-top-style:dotted;border-top-width:2px;}' +
        '#pj-pos .bds{position:absolute;top:-11px;height:22px;display:flex;gap:4px;pointer-events:auto;}' +
        '#pj-pos .bd{display:flex;align-items:center;padding:0 7px;border:1px dashed;border-radius:4px;background:#0d1117;' +
        'font:700 11.5px "Source Sans Pro",system-ui,sans-serif;cursor:ns-resize;user-select:none;}' +
        '#pj-pos .bd:hover{background:#161b22;}' +
        '#pj-pos .cn{position:absolute;width:0;border-left:1px solid;}' +
        '#pj-pos .cn:before,#pj-pos .cn:after{content:"";position:absolute;left:-4px;width:7px;height:7px;border-radius:50%;background:inherit;}' +
        '#pj-pos .cn:before{top:-3px;}#pj-pos .cn:after{bottom:-3px;}' +
        '#pj-pos-aviso{position:absolute;left:50%;top:40px;transform:translateX(-50%);padding:7px 14px;border-radius:8px;' +
        'background:#161b22;border:1px solid #30363d;color:#e6edf3;font:600 12.5px "Source Sans Pro",system-ui,sans-serif;' +
        'box-shadow:0 6px 20px rgba(0,0,0,.5);transition:opacity .25s;white-space:nowrap;z-index:3;}' +
        '#pj-menu{position:absolute;min-width:230px;background:#161b22;border:1px solid #30363d;border-radius:8px;padding:5px 0;' +
        'pointer-events:auto;box-shadow:0 10px 30px rgba(0,0,0,.6);font:13px "Source Sans Pro",system-ui,sans-serif;z-index:4;}' +
        '#pj-menu .it{display:flex;align-items:center;gap:10px;padding:7px 14px;color:#e6edf3;cursor:pointer;white-space:nowrap;}' +
        '#pj-menu .it:hover{background:#1f6feb;}' +
        '#pj-menu .it .px{margin-left:auto;padding-left:18px;color:#8b949e;font-family:ui-monospace,Consolas,monospace;}' +
        '#pj-menu .it:hover .px{color:#e6edf3;}' +
        '#pj-menu .ic{width:14px;text-align:center;font-weight:700;}' +
        '#pj-menu .sep{height:1px;background:#30363d;margin:5px 0;}' +
        '#pj-menu .dis{color:#6e7681;cursor:default;}#pj-menu .dis:hover{background:none;}' +
        '#pj-menu .tit{color:#8b949e;font-size:11.5px;padding:4px 14px 6px;}' +
        '#pj-conf{position:absolute;left:50%;top:45%;transform:translate(-50%,-50%);min-width:300px;background:#0d1117;' +
        'border:1px solid #30363d;border-radius:12px;padding:14px 16px;pointer-events:auto;z-index:5;' +
        'box-shadow:0 14px 40px rgba(0,0,0,.65);font:13px "Source Sans Pro",system-ui,sans-serif;color:#c9d1d9;}' +
        '#pj-conf .t{color:#e6edf3;font-weight:700;font-size:14px;margin-bottom:6px;}' +
        '#pj-conf .d{margin-bottom:12px;line-height:1.45;}' +
        '#pj-conf .d b{color:#e6edf3;}' +
        '#pj-conf .bs{display:flex;gap:8px;}' +
        '#pj-conf button{flex:1;height:32px;border-radius:7px;border:1px solid #30363d;background:#161b22;color:#e6edf3;' +
        'font:600 13px "Source Sans Pro",system-ui,sans-serif;cursor:pointer;}' +
        '#pj-conf button.ok{background:linear-gradient(90deg,#ff4b4b,#ff8f00);border:none;color:#fff;}' +
        '#pj-conf .h{color:#8b949e;font-size:11.5px;margin-top:9px;}' +
        '#pj-conf .h a{color:#ff8f00;cursor:pointer;font-weight:600;}#pj-conf .h a:hover{text-decoration:underline;}' +
        '#pj-ed{position:absolute;left:50%;top:46%;transform:translate(-50%,-50%);width:540px;max-width:94%;background:#0d1117;' +
        'border:1px solid #30363d;border-radius:12px;pointer-events:auto;z-index:7;box-shadow:0 18px 50px rgba(0,0,0,.7);' +
        'font:13px "Source Sans Pro",system-ui,sans-serif;color:#c9d1d9;overflow:hidden;}' +
        '#pj-ed .hd{display:flex;align-items:center;justify-content:space-between;padding:11px 16px;background:#161b22;' +
        'border-bottom:1px solid #30363d;color:#e6edf3;font-weight:700;font-size:14px;}' +
        '#pj-ed .cx{cursor:pointer;color:#8b949e;font-size:15px;}#pj-ed .cx:hover{color:#fff;}' +
        '#pj-ed .cuerpo{display:flex;gap:18px;padding:16px;}' +
        '#pj-ed .campos{display:grid;grid-template-columns:auto 190px;gap:9px 12px;align-items:center;}' +
        '#pj-ed label{color:#8b949e;text-align:right;}' +
        '#pj-ed input,#pj-ed select{height:30px;background:#161b22;border:1px solid #30363d;border-radius:6px;color:#e6edf3;' +
        'padding:0 8px;font:13px ui-monospace,Consolas,monospace;outline:none;color-scheme:dark;box-sizing:border-box;width:100%;}' +
        '#pj-ed select{font-family:"Source Sans Pro",system-ui,sans-serif;}' +
        '#pj-ed input:focus,#pj-ed select:focus{border-color:#ff8f00;}' +
        '#pj-ed input:disabled{opacity:.45;}' +
        '#pj-ed .cot{flex:1;min-width:0;display:flex;flex-direction:column;align-items:stretch;justify-content:center;gap:8px;' +
        'background:#0f1620;border:1px solid #202a37;border-radius:10px;padding:10px;}' +
        '#pj-ed .fila{display:flex;align-items:baseline;justify-content:space-between;gap:10px;}' +
        '#pj-ed .fila .k{color:#8b949e;font-size:12px;}' +
        '#pj-ed .fila .v{font:700 19px ui-monospace,Consolas,monospace;white-space:nowrap;}' +
        '#pj-ed .proy{display:flex;flex-direction:column;gap:3px;border-top:1px solid #202a37;padding-top:8px;' +
        'font:12px ui-monospace,Consolas,monospace;}' +
        '#pj-ed .proy:empty{display:none;}' +
        '#pj-ed .msg{min-height:18px;padding:0 16px;color:#f85149;font-size:12.5px;}' +
        '#pj-ed .bs{display:flex;gap:10px;padding:8px 16px 4px;}' +
        '#pj-ed button{flex:1;height:34px;border-radius:7px;border:none;font:600 13.5px "Source Sans Pro",system-ui,sans-serif;cursor:pointer;color:#fff;}' +
        '#pj-ed button.ok{background:linear-gradient(90deg,#ff4b4b,#ff8f00);}' +
        '#pj-ed button.del{background:#da3633;}' +
        '#pj-ed button:disabled{opacity:.4;cursor:default;}' +
        '#pj-ed .nt{color:#8b949e;font-size:11.5px;text-align:center;padding:6px 16px 14px;}';
      document.head.appendChild(est);
      var capa = document.createElement('div'); capa.id = 'pj-pos';
      containerEl.parentNode.appendChild(capa);
      var ITEMS = {}, nodos = {}, drag = null, tAviso = null, menu = null, conf = null;
      // Etiqueta del precio en vivo (la nativa del gráfico se apagó en central_panel):
      // la dibujamos nosotros para que mida igual que las demás, llegue al borde y mande en el apilado.
      var liveEl = document.createElement('div'); liveEl.className = 'ej ejlive';
      liveEl.style.display = 'none'; capa.appendChild(liveEl);

      function fmt(v, d){ return Number(v).toLocaleString('en-US', {minimumFractionDigits: d, maximumFractionDigits: d}); }
      function txt(el, t){ if (el.textContent !== t) el.textContent = t; }
      function redondear(px){ var f = Math.pow(10, DIGITS); return Math.round(px * f) / f; }
      function esCompra(it){ return it.t === 0 || it.t === 2 || it.t === 4; }
      function precioEntrada(it, n){ return (n && n.pend.po !== undefined) ? n.pend.po : it.po; }
      // P/G si el precio llega a `px` (k = valor de 1 unidad de precio por lote)
      function pgEn(it, entrada, px){ return (esCompra(it) ? 1 : -1) * (px - entrada) * (it.k || K) * it.v; }
      function etiqueta(it){ return TIPO[it.t] + ' ' + fmt(it.v, 2); }

      // '' si es válido; si no, el motivo
      function validar(it, f, px, entrada){
        var m = it.sm || SM;
        if (f === 'po'){
          if (!BID || !ASK) return '';
          if (it.t === 2 && !(px < ASK - m)) return 'un Buy Limit debe quedar bajo el precio actual (Ask)';
          if (it.t === 4 && !(px > ASK + m)) return 'un Buy Stop debe quedar sobre el precio actual (Ask)';
          if (it.t === 3 && !(px > BID + m)) return 'un Sell Limit debe quedar sobre el precio actual (Bid)';
          if (it.t === 5 && !(px < BID - m)) return 'un Sell Stop debe quedar bajo el precio actual (Bid)';
          return '';
        }
        // posición: contra el precio actual; orden pendiente: contra su precio de entrada
        var ref = it.kind === 'ord' ? entrada : (it.pc || it.po), c = esCompra(it);
        var donde = it.kind === 'ord' ? 'el precio de entrada' : 'el precio actual';
        if (f === 'sl' && c && !(px < ref - m)) return 'en una compra el Stop Loss debe quedar bajo ' + donde;
        if (f === 'sl' && !c && !(px > ref + m)) return 'en una venta el Stop Loss debe quedar sobre ' + donde;
        if (f === 'tp' && c && !(px > ref + m)) return 'en una compra el Take Profit debe quedar sobre ' + donde;
        if (f === 'tp' && !c && !(px < ref - m)) return 'en una venta el Take Profit debe quedar bajo ' + donde;
        return '';
      }

      function avisar(t, malo){
        var el = document.getElementById('pj-pos-aviso');
        if (!el){ el = document.createElement('div'); el.id = 'pj-pos-aviso'; capa.appendChild(el); }
        el.textContent = t;
        el.style.borderColor = malo ? '#da3633' : '#2ea043';
        el.style.opacity = '1';
        clearTimeout(tAviso);
        tAviso = setTimeout(function(){ el.style.opacity = '0'; }, 3800);
      }

      // ---------- One-Click Trading: estado del interruptor del ticket ----------
      function ocInput(){ try { return PD.querySelector('.st-key-ord_oc input[type="checkbox"]'); } catch(e){ return null; } }
      function oneClick(){ var i = ocInput(); return !!(i && i.checked); }
      function alternarOneClick(){
        var i = ocInput();
        if (i) i.click();   // mismo interruptor del ticket: la 1.ª vez pide aceptar los términos
        else avisar('Abre el ticket de órdenes para cambiar One-Click Trading', true);
      }

      // Ejecuta `fn` al instante (One-Click) o tras confirmar en el gráfico
      function accion(titulo, desc, fn, alCancelar){
        cerrarConf(true);
        if (oneClick()){ fn(); return; }
        conf = document.createElement('div'); conf.id = 'pj-conf';
        conf.innerHTML = '<div class="t"></div><div class="d"></div><div class="bs">' +
          '<button class="no">Cancelar</button><button class="ok">Confirmar</button></div>' +
          '<div class="h"><a class="oc">Activar One-Click Trading</a> para operar sin confirmar.</div>';
        conf.querySelector('.t').textContent = titulo;
        conf.querySelector('.d').innerHTML = desc;
        conf._cancelar = alCancelar;
        conf.addEventListener('mousedown', function(e){ e.stopPropagation(); });
        conf.querySelector('.no').onclick = function(){ cerrarConf(true); };
        conf.querySelector('.ok').onclick = function(){ cerrarConf(false); fn(); };
        conf.querySelector('.oc').onclick = function(){ cerrarConf(true); alternarOneClick(); };
        capa.appendChild(conf);
      }
      function cerrarConf(cancelar){
        if (!conf) return;
        if (cancelar && conf._cancelar) conf._cancelar();
        if (conf.parentNode) conf.parentNode.removeChild(conf);
        conf = null;
      }

      function post(ruta, cuerpo){
        // text/plain = petición "simple" (sin preflight CORS)
        return fetch(API + ruta, {method: 'POST', headers: {'Content-Type': 'text/plain'}, body: JSON.stringify(cuerpo)})
          .then(function(r){ return r.json(); })
          .catch(function(){ return {error: 'Sin conexión con el servidor de datos'}; });
      }

      // Cambia SL / TP / precio de entrada de una posición u orden (px 0 = quitar SL/TP)
      function cambiarNivel(id, f, px){
        var it = ITEMS[id], n = nodos[id];
        if (!it || !n) return;
        n.pend[f] = px;
        var titulo = f === 'po' ? 'Mover ' + TIPO[it.t] : (px ? NOMBRE[f] : 'Quitar ' + NOMBRE[f]);
        var desc = '<b>' + etiqueta(it) + '</b> ' + REAL + (it.kind === 'ord' ? ' @ ' + fmt(it.po, DIGITS) : '') + '<br>' +
          (f === 'po' ? 'Nuevo precio de entrada: <b>' + fmt(px, DIGITS) + '</b>'
                      : (px ? NOMBRE[f] + ' en <b>' + fmt(px, DIGITS) + '</b>' : 'Se quitará el ' + NOMBRE[f]));
        accion(titulo, desc, function(){
          var cuerpo = {ticket: +it.tk};
          cuerpo[f === 'po' ? 'precio' : f] = px;
          post(it.kind === 'pos' ? '/sltp' : '/orden/modificar', cuerpo).then(function(res){
            delete n.pend[f];
            if (res.error){ avisar(res.error, true); return; }
            var src = it.kind === 'pos' ? POS[it.tk] : ORD[it.tk];
            if (src){ src.sl = res.sl; src.tp = res.tp; if (res.price) src.po = res.price; }
            avisar(f === 'po' ? TIPO[it.t] + ' movido a ' + fmt(px, DIGITS)
                              : (px ? NOMBRE[f] + ' en ' + fmt(px, DIGITS) : NOMBRE[f] + ' eliminado'), false);
          });
        }, function(){ delete n.pend[f]; });
      }

      function cancelarOrden(id){
        var it = ITEMS[id], n = nodos[id];
        if (!it || !n) return;
        n.pend.del = true;
        accion('Cancelar orden pendiente', '<b>' + etiqueta(it) + '</b> ' + REAL + ' @ ' + fmt(it.po, DIGITS), function(){
          post('/orden/eliminar', {ticket: +it.tk}).then(function(res){
            delete n.pend.del;
            if (res.error){ avisar(res.error, true); return; }
            delete ORD[it.tk]; unir();
            avisar(TIPO[it.t] + ' cancelada', false);
          });
        }, function(){ delete n.pend.del; });
      }

      function volumenTicket(){
        try {
          var i = PD.querySelector('.st-key-ord_vol input');
          var v = i ? parseFloat(String(i.value).replace(',', '.')) : NaN;
          return v > 0 ? v : VMIN;
        } catch(e){ return VMIN; }
      }

      function nuevaOrden(nombre, px){
        var vol = volumenTicket(), lado = nombre.indexOf('Buy') === 0 ? 'BUY' : 'SELL';
        accion('Nueva orden pendiente', '<b>' + nombre + ' ' + fmt(vol, 2) + '</b> ' + REAL +
               ' @ <b>' + fmt(px, DIGITS) + '</b><br>Good till cancelled (GTC)', function(){
          post('/orden', {symbol: REAL, lado: lado, volumen: vol, precio: px}).then(function(res){
            if (res.error){ avisar(res.error, true); return; }
            if (res.order){
              var t = {'Buy Limit': 2, 'Sell Limit': 3, 'Buy Stop': 4, 'Sell Stop': 5}[res.tipo] || (lado === 'BUY' ? 2 : 3);
              ORD[String(res.order)] = {s: REAL, t: t, v: res.volume, po: res.price, sl: 0, tp: 0, k: K, sm: SM};
              unir();
            }
            avisar((res.tipo || nombre) + ' ' + fmt(vol, 2) + ' colocada @ ' + fmt(res.price || px, DIGITS), false);
          });
        });
      }

      // ---------- Menú del clic derecho ----------
      function cerrarMenu(){ if (menu && menu.parentNode) menu.parentNode.removeChild(menu); menu = null; }
      containerEl.addEventListener('contextmenu', function(e){
        e.preventDefault();
        if (!serie) return;
        cerrarMenu();
        var r = containerEl.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
        var px = serie.coordinateToPrice(y);
        if (px === null) return;
        px = redondear(px);
        var vol = volumenTicket(), ops = [], oc = oneClick();
        if (BID && ASK){
          if (px < BID - SM) ops = [['Buy Limit', COMPRA, '▲'], ['Sell Stop', VENTA, '▼']];
          else if (px > ASK + SM) ops = [['Sell Limit', VENTA, '▼'], ['Buy Stop', COMPRA, '▲']];
        }
        menu = document.createElement('div'); menu.id = 'pj-menu';
        var h = '<div class="tit">' + REAL + ' · ' + fmt(px, DIGITS) + '</div>';
        if (ops.length){
          ops.forEach(function(o, i){
            h += '<div class="it" data-i="' + i + '"><span class="ic" style="color:' + o[1] + '">' + o[2] + '</span>' +
                 o[0] + ' ' + fmt(vol, 2) + '<span class="px">' + fmt(px, DIGITS) + '</span></div>';
          });
        } else {
          h += '<div class="it dis"><span class="ic">·</span>' + (BID ? 'Precio dentro del spread' : 'Sin precio en vivo') + '</div>';
        }
        h += '<div class="sep"></div><div class="it" data-oc="1"><span class="ic" style="color:#ff8f00">' +
             (oc ? '✓' : '⚡') + '</span>One-Click Trading<span class="px">' + (oc ? 'ON' : 'OFF') + '</span></div>';
        menu.innerHTML = h;
        menu.style.left = Math.max(0, Math.min(x, containerEl.clientWidth - 250)) + 'px';
        menu.style.top = Math.max(0, Math.min(y, containerEl.clientHeight - 150)) + 'px';
        menu.addEventListener('mousedown', function(ev){ ev.stopPropagation(); });
        menu.addEventListener('click', function(ev){
          var it = ev.target.closest('.it');
          if (!it || it.classList.contains('dis')) return;
          cerrarMenu();
          if (it.getAttribute('data-oc')){ alternarOneClick(); return; }
          nuevaOrden(ops[+it.getAttribute('data-i')][0], px);
        });
        capa.appendChild(menu);
      }, true);
      document.addEventListener('mousedown', function(){ cerrarMenu(); });

      // ---------- Ventana "Modificar orden" (como MT5): doble clic o clic derecho en la línea ----------
      var ed = null, edPrev = null;
      function aLocal(exServidor){            // hora del servidor (s) -> valor de datetime-local
        var d = new Date((exServidor - OFF) * 1000), z = function(n){ return (n < 10 ? '0' : '') + n; };
        return d.getFullYear() + '-' + z(d.getMonth() + 1) + '-' + z(d.getDate()) + 'T' + z(d.getHours()) + ':' + z(d.getMinutes());
      }
      function aServidor(valorLocal){         // datetime-local -> hora del servidor (s)
        var t = new Date(valorLocal).getTime();
        return isNaN(t) ? 0 : Math.round(t / 1000 + OFF);
      }
      function cerrarEditor(){
        if (ed && ed.parentNode) ed.parentNode.removeChild(ed);
        ed = null; edPrev = null;
      }
      function menuOrden(e, id){
        e.preventDefault(); e.stopPropagation();
        cerrarMenu();
        var it = ITEMS[id]; if (!it) return;
        var r = containerEl.getBoundingClientRect();
        menu = document.createElement('div'); menu.id = 'pj-menu';
        var nom = '#' + it.tk + ' ' + TIPO[it.t].toLowerCase() + ' ' + fmt(it.v, 2);
        menu.innerHTML = '<div class="it" data-a="mod"><span class="ic" style="color:#58a6ff">&#9881;</span>Modificar ' + nom +
          '<span class="px">' + fmt(it.po, DIGITS) + '</span></div>' +
          '<div class="it" data-a="del"><span class="ic" style="color:#f85149">&#10005;</span>Eliminar ' + nom +
          '<span class="px">' + fmt(it.po, DIGITS) + '</span></div>';
        menu.style.left = Math.max(0, Math.min(e.clientX - r.left, containerEl.clientWidth - 330)) + 'px';
        menu.style.top = Math.max(0, Math.min(e.clientY - r.top, containerEl.clientHeight - 90)) + 'px';
        menu.addEventListener('mousedown', function(ev){ ev.stopPropagation(); });
        menu.addEventListener('click', function(ev){
          var x = ev.target.closest('.it'); if (!x) return;
          cerrarMenu();
          if (x.getAttribute('data-a') === 'mod') abrirEditor(id); else cancelarOrden(id);
        });
        capa.appendChild(menu);
      }
      function abrirEditor(id){
        cerrarMenu(); cerrarConf(true); cerrarEditor();
        var it = ITEMS[id];
        if (!it || it.kind !== 'ord') return;
        var paso = Math.pow(10, -DIGITS);
        ed = document.createElement('div'); ed.id = 'pj-ed';
        ed.innerHTML =
          '<div class="hd"><span class="tt"></span><span class="cx" title="Cerrar">&#10005;</span></div>' +
          '<div class="cuerpo"><div class="campos">' +
            '<label>Precio</label><input class="i-po" type="number" step="' + paso + '">' +
            '<label>Stop Loss</label><input class="i-sl" type="number" step="' + paso + '" min="0">' +
            '<label>Take Profit</label><input class="i-tp" type="number" step="' + paso + '" min="0">' +
            '<label>Caducidad</label><select class="i-tt"><option value="gtc">Good till cancelled (GTC)</option>' +
              '<option value="day">Day</option><option value="specified">Specified (fecha)</option></select>' +
            '<label class="l-ex">Fecha caducidad</label><input class="i-ex" type="datetime-local">' +
          '</div><div class="cot">' +
            '<div class="fila"><span class="k">Bid</span><span class="v b" style="color:' + VENTA + '"></span></div>' +
            '<div class="fila"><span class="k">Ask</span><span class="v a" style="color:' + COMPRA + '"></span></div>' +
            '<div class="proy"></div></div></div>' +
          '<div class="msg"></div>' +
          '<div class="bs"><button class="ok">Modificar</button><button class="del">Eliminar</button></div>' +
          '<div class="nt">El precio de entrada debe ' + (SM > 0 ? 'estar al menos a ' + fmt(SM, DIGITS) + ' del' : 'ser distinto del') +
          ' precio de mercado; lo mismo para Stop Loss y Take Profit. 0 = sin Stop Loss / Take Profit.</div>';
        ed.querySelector('.tt').textContent = 'Modificar orden #' + it.tk + ' · ' + TIPO[it.t] + ' ' + fmt(it.v, 2) + ' ' + REAL;
        var q = function(c){ return ed.querySelector(c); };
        q('.i-po').value = (+it.po).toFixed(DIGITS);
        q('.i-sl').value = (+it.sl || 0).toFixed(DIGITS);
        q('.i-tp').value = (+it.tp || 0).toFixed(DIGITS);
        var cad = ['gtc', 'day', 'specified'][it.tt || 0] || 'gtc';
        q('.i-tt').value = cad;
        [['gtc', 1], ['day', 2], ['specified', 4]].forEach(function(m){       // modos que admite el bróker
          if (EM && !(EM & m[1])) q('.i-tt option[value="' + m[0] + '"]').disabled = true;
        });
        q('.i-ex').value = aLocal(it.ex ? it.ex : Math.round(Date.now() / 1000 + OFF + 86400));
        var exIni = q('.i-ex').value;
        function leer(){
          return {po: parseFloat(q('.i-po').value), sl: parseFloat(q('.i-sl').value) || 0,
                  tp: parseFloat(q('.i-tp').value) || 0, tt: q('.i-tt').value, ex: q('.i-ex').value};
        }
        function revisar(){
          if (!ed) return;
          var v = leer(), err = '';
          var fecha = v.tt === 'specified';
          q('.i-ex').disabled = !fecha; q('.l-ex').style.opacity = fecha ? 1 : .45;
          if (isNaN(v.po) || v.po <= 0) err = 'Precio inválido';
          else err = validar(it, 'po', v.po, v.po) || (v.sl > 0 && validar(it, 'sl', v.sl, v.po)) ||
                     (v.tp > 0 && validar(it, 'tp', v.tp, v.po)) || '';
          if (!err && fecha && aServidor(v.ex) <= Date.now() / 1000 + OFF) err = 'la fecha de caducidad debe ser futura';
          var cambio = redondear(v.po) !== redondear(it.po) || redondear(v.sl) !== redondear(+it.sl || 0) ||
                       redondear(v.tp) !== redondear(+it.tp || 0) || v.tt !== cad || (fecha && v.ex !== exIni);
          q('.ok').disabled = !!err || !cambio;
          q('.msg').textContent = err ? 'No válido: ' + err : '';
          edPrev = isNaN(v.po) ? null : {id: id, po: v.po, sl: v.sl, tp: v.tp};
          var g = v.tp > 0 ? pgEn(it, v.po, v.tp) : null, l = v.sl > 0 ? pgEn(it, v.po, v.sl) : null;
          q('.proy').innerHTML = (g !== null ? '<span style="color:' + C_TP + '">TP ' + pgTxt(g) + '</span>' : '') +
                               (l !== null ? '<span style="color:' + C_SL + '">SL ' + pgTxt(l) + '</span>' : '');
        }
        ed._revisar = revisar;
        ed.addEventListener('input', revisar);
        ed.addEventListener('change', revisar);
        // que escribir aquí no active los atajos del gráfico (Supr borra dibujos, etc.)
        ed.addEventListener('keydown', function(e){
          e.stopPropagation();
          if (e.key === 'Escape') cerrarEditor();
          if (e.key === 'Enter' && !q('.ok').disabled) q('.ok').click();
        });
        ed.addEventListener('mousedown', function(e){ e.stopPropagation(); });
        q('.cx').onclick = cerrarEditor;
        q('.del').onclick = function(){
          q('.del').disabled = q('.ok').disabled = true;
          post('/orden/eliminar', {ticket: +it.tk}).then(function(res){
            if (res.error){ q('.msg').textContent = res.error; q('.del').disabled = false; revisar(); return; }
            delete ORD[it.tk]; unir(); cerrarEditor();
            avisar(TIPO[it.t] + ' #' + it.tk + ' eliminada', false);
          });
        };
        q('.ok').onclick = function(){
          var v = leer();
          q('.ok').disabled = q('.del').disabled = true; q('.ok').textContent = 'Enviando…';
          post('/orden/modificar', {ticket: +it.tk, precio: redondear(v.po), sl: redondear(v.sl), tp: redondear(v.tp),
                                    caducidad: v.tt, expiracion: v.tt === 'specified' ? aServidor(v.ex) : 0})
            .then(function(res){
              if (!ed) return;
              if (res.error){
                q('.msg').textContent = res.error; q('.ok').textContent = 'Modificar'; q('.del').disabled = false; revisar();
                return;
              }
              var src = ORD[it.tk];
              if (src){ src.po = res.price; src.sl = res.sl; src.tp = res.tp; src.tt = res.tt; src.ex = res.ex; }
              cerrarEditor();
              avisar(TIPO[it.t] + ' #' + it.tk + ' modificada', false);
            });
        };
        capa.appendChild(ed);
        revisar();
        q('.i-po').focus();
      }

      // ---------- Líneas ----------
      function crearLinea(clase){
        var el = document.createElement('div'); el.className = 'pl ' + clase;
        el.innerHTML = '<div class="ln"></div><div class="tg"><span class="vo"></span><span class="pg"></span>' +
                       '<span class="x">&#10005;</span></div><div class="ej"></div>';
        el.style.display = 'none';
        capa.appendChild(el);
        return el;
      }

      function empezar(id, f, e){
        if (e.button !== 0) return;
        if (f === 'sl' && ITEMS[id] && ITEMS[id].tr){
          e.preventDefault(); e.stopPropagation();
          avisar('El Stop Loss está en automático (stop dinámico). Para cambiarlo, edita la distancia en Cartera.', true);
          return;
        }
        e.preventDefault(); e.stopPropagation();
        cerrarMenu(); cerrarConf(true);
        drag = {id: id, f: f, px: null, y0: e.clientY, movido: false};
        document.body.style.cursor = 'ns-resize';
      }

      function crear(id){
        var it = ITEMS[id];
        var n = {main: crearLinea(it.kind === 'ord' ? 'po' : 'pm'), tp: crearLinea('lv'), sl: crearLinea('lv'), pend: {}};
        n.con = document.createElement('div'); n.con.className = 'cn'; capa.appendChild(n.con);
        n.bds = document.createElement('div'); n.bds.className = 'bds';
        n.bds.innerHTML = '<span class="bd" title="Arrastrar para añadir Take Profit">TP</span>' +
                          '<span class="bd" title="Arrastrar para añadir Stop Loss">SL</span>';
        capa.appendChild(n.bds);
        n.bdTp = n.bds.children[0]; n.bdSl = n.bds.children[1];
        n.bdTp.style.color = C_TP; n.bdTp.style.borderColor = C_TP;
        n.bdSl.style.color = C_SL; n.bdSl.style.borderColor = C_SL;
        n.bdTp.addEventListener('mousedown', function(e){ empezar(id, 'tp', e); });
        n.bdSl.addEventListener('mousedown', function(e){ empezar(id, 'sl', e); });
        var x = n.main.querySelector('.x');
        x.addEventListener('mousedown', function(e){ e.stopPropagation(); });
        if (it.kind === 'pos'){
          // ✕ de la posición → modal de cierre (botón invisible de Python, gatillos_cierre)
          x.title = 'Cerrar posición';
          x.addEventListener('click', function(e){
            e.stopPropagation();
            try { var b = PD.querySelector('.st-key-chcls_' + it.tk + ' button'); if (b) b.click(); } catch(err) {}
          });
        } else {
          x.title = 'Cancelar orden';
          x.addEventListener('click', function(e){ e.stopPropagation(); cancelarOrden(id); });
          var tgo = n.main.querySelector('.tg');
          tgo.title = 'Arrastrar para mover · doble clic o clic derecho para modificar';
          tgo.addEventListener('mousedown', function(e){ if (e.detail < 2) empezar(id, 'po', e); });
          tgo.addEventListener('dblclick', function(e){ e.stopPropagation(); drag = null; document.body.style.cursor = ''; abrirEditor(id); });
          tgo.addEventListener('contextmenu', function(e){ menuOrden(e, id); });
        }
        ['tp', 'sl'].forEach(function(f){
          var lv = n[f], lx = lv.querySelector('.x');
          lx.title = 'Quitar ' + NOMBRE[f];
          lx.addEventListener('mousedown', function(e){ e.stopPropagation(); });
          lx.addEventListener('click', function(e){
            e.stopPropagation();
            // SL en automático (stop dinámico): el motor lo repone enseguida, así que
            // quitarlo desde aquí no sirve (reaparece). Se bloquea como el arrastre.
            if (f === 'sl' && ITEMS[id] && ITEMS[id].tr){
              avisar('El Stop Loss está en automático (stop dinámico). Para quitarlo, desactiva el stop dinámico en Cartera.', true);
              return;
            }
            cambiarNivel(id, f, 0);
          });
          lv.querySelector('.tg').title = 'Arrastrar para mover el ' + NOMBRE[f];
          lv.querySelector('.tg').addEventListener('mousedown', function(e){ empezar(id, f, e); });
        });
        return n;
      }

      function borrar(id){
        var n = nodos[id];
        [n.main, n.tp, n.sl, n.con, n.bds].forEach(function(el){ if (el.parentNode) el.parentNode.removeChild(el); });
        delete nodos[id];
      }

      // Une posiciones y órdenes en ITEMS y crea/borra sus líneas
      function unir(){
        var nuevo = {};
        for (var a in POS){ POS[a].kind = 'pos'; POS[a].tk = a; nuevo['p' + a] = POS[a]; }
        for (var b in ORD){ ORD[b].kind = 'ord'; ORD[b].tk = b; nuevo['o' + b] = ORD[b]; }
        ITEMS = nuevo;
        for (var id in nodos){ if (!ITEMS[id]) borrar(id); }
        for (var id2 in ITEMS){ if (!nodos[id2]) nodos[id2] = crear(id2); }
      }

      function mover(e){
        if (!drag || !serie) return;
        if (!drag.movido && Math.abs(e.clientY - drag.y0) < 4) return;   // un clic no es un arrastre
        drag.movido = true;
        var r = containerEl.getBoundingClientRect();
        var px = serie.coordinateToPrice(e.clientY - r.top);
        if (px !== null) drag.px = redondear(px);
      }
      function soltar(cancelar){
        if (!drag) return;
        var d = drag; drag = null;
        document.body.style.cursor = '';
        var it = ITEMS[d.id];
        if (cancelar || !it || d.px === null || !d.movido) return;
        var actual = d.f === 'po' ? precioEntrada(it, nodos[d.id]) : (+it[d.f] || 0);
        if (redondear(actual) === d.px) return;                          // mismo precio: nada que enviar
        var motivo = validar(it, d.f, d.px, precioEntrada(it, nodos[d.id]));
        if (motivo){ avisar('No válido: ' + motivo, true); return; }
        cambiarNivel(d.id, d.f, d.px);
      }
      document.addEventListener('mousemove', function(e){
        if (!drag) return;
        if (e.buttons === 0){ soltar(true); return; }   // se soltó fuera del gráfico
        mover(e);
      });
      document.addEventListener('mouseup', function(){ soltar(false); });
      document.addEventListener('keydown', function(e){
        if (e.key === 'Escape'){ soltar(true); cerrarMenu(); cerrarConf(true); cerrarEditor(); }
      });

      // Dibuja una línea en la altura del precio dado
      function colocar(el, y, w, h, eje, col, vo, pg, pgCol, pxEje, nivel, esOrden){
        if (y === null || y < 0 || y > h - 28){ el.style.display = 'none'; return false; }
        el.style.display = '';
        el.style.top = Math.round(y) + 'px';
        el.style.width = w + 'px';
        var ln = el.querySelector('.ln'), v = el.querySelector('.vo'), g = el.querySelector('.pg'),
            x = el.querySelector('.x'), ej = el.querySelector('.ej'), tg = el.querySelector('.tg');
        // ORDEN PENDIENTE: borde punteado en etiqueta y recuadro (como su línea), relleno intacto.
        var ord = esOrden && !nivel, bs = ord ? 'dashed' : 'solid';
        ln.style.width = (w - eje) + 'px';
        ln.style.borderTopColor = col;
        tg.style.right = (eje + SEP) + 'px';
        txt(v, vo);
        if (nivel){ v.style.background = '#161b22'; v.style.color = col; v.style.borderColor = col; }
        else { v.style.background = col; v.style.color = '#fff';
               v.style.borderColor = ord ? '#0d1117' : col; }   // punteado oscuro visible sobre el relleno
        v.style.borderStyle = bs;
        txt(g, pg);
        g.style.color = pgCol;
        g.style.borderColor = col; g.style.borderStyle = bs;
        x.style.borderColor = col; x.style.borderLeftColor = '#30363d'; x.style.borderStyle = bs;
        // Recuadro del eje: posiciones/órdenes RELLENO; niveles TP/SL solo CONTORNO
        // (como XM: así el TP/SL no se confunde con una posición). Las órdenes pendientes
        // llevan el borde punteado para distinguirse de las posiciones abiertas.
        ej.style.width = eje + 'px';
        if (nivel){ ej.style.background = '#0d1117'; ej.style.color = col;
                    ej.style.boxShadow = 'inset 0 0 0 1.5px ' + col; ej.style.border = 'none'; }
        else { ej.style.background = col; ej.style.color = '#fff'; ej.style.boxShadow = 'none';
               ej.style.border = ord ? '1.5px dashed #0d1117' : 'none'; }
        txt(ej, fmt(pxEje, DIGITS));
        return true;
      }
      function pgTxt(v){ return (v >= 0 ? '+' : '') + fmt(v, 2) + ' USD'; }

      // Cada frame: alturas (zoom, desplazamiento, autoescala) y arrastres
      function ubicar(){
        requestAnimationFrame(ubicar);
        if (!serie) return;
        var w = containerEl.clientWidth, h = containerEl.clientHeight;
        capa.style.left = containerEl.offsetLeft + 'px'; capa.style.top = containerEl.offsetTop + 'px';
        capa.style.width = w + 'px'; capa.style.height = h + 'px';
        var eje = 72;
        try { eje = chart.priceScale('right').width() || 72; } catch(e) {}
        var yLive = (BID && serie) ? serie.priceToCoordinate(BID) : null;   // y del recuadro blanco del precio en vivo
        var cajas = [];   // recuadros del eje visibles (para apilarlos sin pisar el blanco)
        if (ed){
          txt(ed.querySelector('.b'), BID ? fmt(BID, DIGITS) : '—');
          txt(ed.querySelector('.a'), ASK ? fmt(ASK, DIGITS) : '—');
          if (!ITEMS[edPrev ? edPrev.id : ''] && edPrev) cerrarEditor();   // la orden se ejecutó o se canceló
        }
        for (var id in nodos){
          var it = ITEMS[id], n = nodos[id];
          if (!it) continue;
          var lado = esCompra(it) ? COMPRA : VENTA;
          var arrPo = drag && drag.id === id && drag.f === 'po';
          var prev = edPrev && edPrev.id === id ? edPrev : null;
          var entrada = arrPo ? drag.px : (prev ? prev.po : precioEntrada(it, n));
          var y0 = serie.priceToCoordinate(entrada), visible;
          if (it.kind === 'pos'){
            visible = colocar(n.main, y0, w, h, eje, lado, (esCompra(it) ? '+' : '-') + fmt(it.v, 2),
                              pgTxt(it.p || 0), (it.p || 0) >= 0 ? COMPRA : VENTA, it.po, false, false);
            n.main.querySelector('.tg').title = TIPO[it.t] + ' ' + fmt(it.v, 2) + ' lote(s) a ' + fmt(it.po, DIGITS);
          } else {
            visible = colocar(n.main, y0, w, h, eje,
                              lado, TIPO[it.t].toUpperCase() + ' ' + fmt(it.v, 2) + (it.oco ? ' · OCO' : ''),
                              'at ' + fmt(entrada, DIGITS), '#c9d1d9', entrada, false, true);
          }
          var malPo = arrPo && validar(it, 'po', entrada, entrada);
          n.main.className = 'pl ' + (it.kind === 'ord' ? 'po' : 'pm') +
            ((n.pend.po !== undefined || n.pend.del) ? ' pend' : '') + (malPo ? ' mal' : '');
          if (visible) cajas.push({ej: n.main.querySelector('.ej'), y: y0});
          var ys = visible ? [y0] : [], hay = {};
          ['tp', 'sl'].forEach(function(f){
            var arrastra = drag && drag.id === id && drag.f === f;
            var px = arrastra ? drag.px : (prev ? prev[f] : (f in n.pend ? n.pend[f] : it[f]));
            var el = n[f];
            if (!px){ el.style.display = 'none'; return; }
            hay[f] = true;
            var col = f === 'tp' ? C_TP : C_SL, g = pgEn(it, entrada, px);
            var y = serie.priceToCoordinate(px);
            var etq = f.toUpperCase() + (f === 'sl' && it.tr ? ' auto' : '') + ' ' + fmt(it.v, 2);
            if (f === 'sl') el.querySelector('.x').title = it.tr
              ? 'Gestionado por el stop dinámico (quítalo en Cartera)' : 'Quitar Stop Loss';
            if (colocar(el, y, w, h, eje, col, etq, pgTxt(g),
                        g >= 0 ? COMPRA : VENTA, px, true, false)){ ys.push(y); cajas.push({ej: el.querySelector('.ej'), y: y}); }
            el.className = 'pl lv' + ((f in n.pend) ? ' pend' : '') +
                           (arrastra && validar(it, f, px, entrada) ? ' mal' : '');
          });
          // Insignias TP / SL (solo para los niveles que faltan)
          n.bdTp.style.display = hay.tp ? 'none' : '';
          n.bdSl.style.display = hay.sl ? 'none' : '';
          if (visible && (!hay.tp || !hay.sl) && !n.pend.del){
            n.bds.style.display = '';
            n.bds.style.top = (Math.round(y0) - 11) + 'px';
            n.bds.style.right = (eje + SEP + n.main.querySelector('.tg').offsetWidth + 6) + 'px';
          } else {
            n.bds.style.display = 'none';
          }
          // Conector vertical entre la línea principal y sus niveles (como XM)
          if (ys.length > 1){
            var a = Math.max(0, Math.min.apply(null, ys)), b = Math.min(h, Math.max.apply(null, ys));
            n.con.style.display = '';
            n.con.style.left = (w - eje - 14) + 'px';
            n.con.style.top = a + 'px'; n.con.style.height = (b - a) + 'px';
            n.con.style.borderLeftColor = lado; n.con.style.background = lado;
          } else {
            n.con.style.display = 'none';
          }
        }

        // ---- Apilado del eje (como XM): el recuadro BLANCO del precio en vivo MANDA
        // (se queda en su sitio) y EMPUJA los nuestros, que quedan PEGADOS (sin hueco).
        // Solo se mueve el chip del eje (.ej); la línea y la etiqueta grande siguen en su
        // precio real. Si no hay precio en vivo, cada recuadro queda en su sitio. ----
        var ALTO = 20;   // = alto del recuadro -> quedan pegados, sin espacio (todos iguales)
        var liveVivo = (yLive !== null && yLive >= 0 && yLive <= h - 10);
        if (liveVivo){
          liveEl.style.display = ''; liveEl.style.width = eje + 'px'; txt(liveEl, fmt(BID, DIGITS));
        } else {
          liveEl.style.display = 'none';
        }
        var lista = cajas.slice();
        if (liveVivo) lista.push({ej: liveEl, y: yLive, ancla: true, abs: true});   // el blanco es el ancla
        lista.sort(function(p, q){ return p.y - q.y; });
        var ia = -1;
        for (var i = 0; i < lista.length; i++){ if (lista[i].ancla){ ia = i; break; } }
        if (ia < 0){
          lista.forEach(function(c){ c.aj = c.y; });              // sin precio en vivo: sin empujar
        } else {
          lista[ia].aj = lista[ia].y;
          for (var i = ia - 1; i >= 0; i--){ lista[i].aj = Math.min(lista[i].y, lista[i + 1].aj - ALTO); }
          for (var i = ia + 1; i < lista.length; i++){ lista[i].aj = Math.max(lista[i].y, lista[i - 1].aj + ALTO); }
        }
        lista.forEach(function(c){
          if (!c.ej) return;
          c.ej.style.top = Math.round(c.abs ? c.aj - 10 : -10 + (c.aj - c.y)) + 'px';
        });
      }

      // En vivo: Bid/Ask (ticks) y altas/bajas/SL/TP/P-G (mensaje de cuenta del feed)
      if ('BroadcastChannel' in window){
        new BroadcastChannel('pj-ticks').addEventListener('message', function(ev){
          var d = ev.data || {};
          var t = d.t && (d.t[SIMBOLO] || d.t[REAL]);
          if (t && t.b){
            BID = t.b; ASK = t.a;
            if (t.t) OFF = Math.round((t.t - Date.now() / 1000) / 900) * 900;
            if (ed && ed._revisar && document.activeElement && !ed.contains(document.activeElement)) ed._revisar();
          }
          var acc = d.acc;
          if (!acc) return;
          if (acc.pi){
            var np = {};
            for (var tk in acc.pi){
              var x = acc.pi[tk];
              if (x.s !== REAL) continue;
              np[tk] = {s: x.s, t: x.t, v: x.v, po: x.po, sl: x.sl, tp: x.tp, k: x.k, sm: x.sm,
                        tr: x.tr, p: (acc.pos || {})[tk], pc: (acc.pc || {})[tk]};
            }
            POS = np;
          } else {
            for (var tk2 in POS){
              if (acc.pos && tk2 in acc.pos) POS[tk2].p = acc.pos[tk2];
              if (acc.pc && tk2 in acc.pc) POS[tk2].pc = acc.pc[tk2];
            }
          }
          if (acc.ord){
            var no = {};
            for (var tk3 in acc.ord){ var o = acc.ord[tk3]; if (o.s === REAL) no[tk3] = o; }
            ORD = no;
          }
          if (acc.pi || acc.ord) unir();
        });
      }
      // ¿El servidor de datos en ejecución es la versión que espera este código?
      var V_API = 5;
      fetch(API + '/salud').then(function(r){ return r.json(); }).then(function(r){
        if (!r.v || r.v < V_API){
          avisar('El servidor de datos está desactualizado: reinicia servidor_datos.py', true);
          var el = document.getElementById('pj-pos-aviso'); clearTimeout(tAviso);
          if (el) el.style.whiteSpace = 'normal';
        }
      }).catch(function(){});
      unir();
      ubicar();
    })();
"""


def js_posiciones(simbolo: str) -> str:
    """JS de trading desde el gráfico para el símbolo cargado."""
    real = resolver_simbolo(simbolo)
    return (_JS.replace("__POS_REAL__", json.dumps(real))
               .replace("__POS_INI__", json.dumps(_iniciales(real))))


@st.fragment(run_every=intervalo("2s", "5s"))   # altas/bajas de posiciones
def gatillos_cierre():
    """Botones invisibles (uno por posición abierta) que pulsa la ✕ del gráfico."""
    try:
        posiciones = obtener_posiciones() or []
    except Exception:
        posiciones = []
    with st.container(key="chcls_wrap"):
        for p in posiciones:
            tk = p.get("ticket")
            if st.button("cerrar", key=f"chcls_{tk}"):
                st.session_state.ca_cerrar = {
                    "ticket": tk, "symbol": (p.get("symbol") or "").replace("...", ""),
                    "profit": _neto(p), "tipo": p.get("tipo"), "volumen": p.get("volumen", 0),
                }
                st.session_state.pop("ca_result", None)
                st.rerun(scope="app")
