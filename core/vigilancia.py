"""Vigilancia automática: el agente analiza un activo cada cierto tiempo y, si el usuario lo autorizó,
compra o vende solo.

NOMBRE DEL ARCHIVO: core/vigilancia.py

Cómo funciona
  1. El usuario pide en el chat que el agente vigile un activo y opere por su cuenta.
  2. El agente llama a la herramienta `proponer_vigilancia`: queda PENDIENTE_AUTORIZACION con sus
     términos (activo, riesgo, máx. operaciones, duración, intervalo). NO hace nada todavía.
  3. El usuario pulsa «Autorizar» en el panel (components/panel_ordenes.py). Solo entonces pasa a ACTIVA.
  4. Un motor en segundo plano (iniciar_motor) despierta cada pocos segundos y, cuando a una vigilancia
     le toca, le pide al agente un análisis. El agente responde con una DECISIÓN estructurada
     (esperar / abrir / cerrar) y el MOTOR (no el modelo) la valida y la ejecuta.
  5. Cada compra, venta o cierre automático avisa en la campana de notificaciones.

Garantías de diseño (están en código, no en el prompt):
  * El modelo NO tiene ninguna herramienta que ejecute órdenes, tampoco en este modo: el registro que
    usa el análisis excluye las de proponer/vigilar. Solo este motor ejecuta, y solo lo autorizado.
  * Solo CUENTA DEMO (se comprueba en la autorización y en cada chequeo, aunque LIMITES.solo_demo se relaje).
  * Solo el activo de la vigilancia, con el riesgo de la vigilancia (nunca más que el límite global).
  * Todas las comprobaciones de core/ordenes.py siguen aplicando: stop loss obligatorio, riesgo total,
    pérdida diaria, interruptor de emergencia, margen, distancia mínima, etc.
  * Tope de operaciones, UNA posición abierta a la vez y vencimiento automático.
  * Solo puede cerrar las posiciones que ella misma abrió (las reconoce por el comentario de la orden).
  * El usuario puede detenerla cuando quiera; si la detiene mientras el modelo analizaba, se descarta.
"""

from __future__ import annotations

import json
import re
import threading
import time
import traceback
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable

import MetaTrader5 as mt5  # type: ignore[import-untyped]

from core import notificaciones, ordenes

# ══════════════════════════════════════════════════════════════
#  Configuración
# ══════════════════════════════════════════════════════════════
INTERVALO_DEFECTO_MIN = 15       # cada cuánto se analiza el activo
INTERVALO_MIN, INTERVALO_MAX = 5, 240
DURACION_DEFECTO_H = 8.0         # la vigilancia termina sola a las N horas de autorizarla
DURACION_MIN_H, DURACION_MAX_H = 0.5, 24.0
MAX_OPERACIONES_DEFECTO = 3      # aperturas máximas por vigilancia
MAX_OPERACIONES_TOPE = 10
RIESGO_DEFECTO_PCT = 0.5         # % del equity por operación si el usuario no indica otro
MAX_VIGILANCIAS_POR_USUARIO = 3  # activas + pendientes de autorizar (acota el gasto de tokens)
MAX_ABIERTAS_POR_VIGILANCIA = 1  # no se acumulan posiciones: una abierta a la vez
ERRORES_SEGUIDOS_MAX = 3         # tras N fallos seguidos del análisis, la vigilancia se detiene
ESPERA_MOTOR_S = 20              # cada cuánto despierta el motor
PERFIL_VIGILANCIA: str | None = None   # None = perfil por defecto del agente (config.PERFIL_POR_DEFECTO)

NOMBRE_HILO_MOTOR = "pj-vigilancia-motor"
PREFIJO_HILO_CHEQUEO = "pj-vigilancia-"

# Estados
PENDIENTE, ACTIVA = "PENDIENTE_AUTORIZACION", "ACTIVA"
FINALIZADA, CANCELADA, EXPIRADA, ERROR = "FINALIZADA", "CANCELADA", "EXPIRADA", "ERROR"
VIGENTES = (PENDIENTE, ACTIVA)

# Herramientas que el análisis automático NO puede usar (ninguna ejecuta o programa órdenes).
HERRAMIENTAS_EXCLUIDAS = frozenset({
    "proponer_orden", "proponer_cierre_posicion", "proponer_vigilancia", "detener_vigilancia", "ver_vigilancias",
})


# ══════════════════════════════════════════════════════════════
#  Utilidades
# ══════════════════════════════════════════════════════════════
def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def _a_numero(valor: Any) -> float | None:
    """Los modelos a veces envían números como texto ('1,25'); None si no es un número."""
    if isinstance(valor, bool) or valor is None or valor == "":
        return None
    try:
        return float(str(valor).replace(",", ".")) if isinstance(valor, str) else float(valor)
    except (TypeError, ValueError):
        return None


def _consultar(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    return ordenes._consultar(sql, params)


def _actualizar(vid: str, **campos: Any) -> None:
    if not campos:
        return
    asignaciones = ", ".join(f"{c} = ?" for c in campos)
    ordenes._ejecutar(f"UPDATE vigilancias SET {asignaciones} WHERE id = ?", (*campos.values(), vid))


def obtener(vid: str) -> dict[str, Any] | None:
    filas = _consultar("SELECT * FROM vigilancias WHERE id = ?", (vid,))
    return filas[0] if filas else None


def _notificar(v: dict[str, Any], titulo: str, texto: str, tipo: str = "auto") -> None:
    try:
        notificaciones.agregar(v["usuario_id"], titulo, texto, tipo=tipo, ref=v["id"])
    except Exception:  # noqa: BLE001 - un fallo al avisar nunca debe tumbar el motor
        traceback.print_exc()


def _lado_txt(lado: str) -> str:
    return "Compra" if str(lado).lower() == "compra" else "Venta"


# ══════════════════════════════════════════════════════════════
#  Gestión de vigilancias (la usan las herramientas del agente y el panel)
# ══════════════════════════════════════════════════════════════
def resumen_terminos(v: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": v["id"], "simbolo": v["simbolo"], "estado": v["estado"],
        "riesgo_por_operacion_pct": v["riesgo_pct"], "max_operaciones": v["max_operaciones"],
        "operaciones_realizadas": v.get("operaciones") or 0,
        "chequeo_cada_min": v["intervalo_min"], "duracion_horas": v["duracion_horas"],
        "puede_cerrar_sus_posiciones": bool(v.get("permite_cerrar")),
    }


def crear(
    usuario_id: str, simbolo: str, instruccion: str = "", riesgo_pct: Any = None,
    max_operaciones: Any = None, duracion_horas: Any = None, intervalo_min: Any = None,
) -> dict[str, Any]:
    """Registra una vigilancia PENDIENTE de autorización. {"ok": False, "motivo"} si no se puede."""
    def no(motivo: str) -> dict[str, Any]:
        return {"ok": False, "motivo": motivo}

    def leer(valor: Any, nombre: str, defecto: float) -> tuple[float | None, str | None]:
        """(valor, error). Sin valor → el de por defecto; con un valor que no es número → error (no se adivina)."""
        if valor is None or valor == "":
            return defecto, None
        n = _a_numero(valor)
        return (n, None) if n is not None else (None, f"'{nombre}' debe ser un número.")

    riesgo, e1 = leer(riesgo_pct, "riesgo_pct", RIESGO_DEFECTO_PCT)
    n_ops, e2 = leer(max_operaciones, "max_operaciones", MAX_OPERACIONES_DEFECTO)
    horas, e3 = leer(duracion_horas, "duracion_horas", DURACION_DEFECTO_H)
    cada, e4 = leer(intervalo_min, "intervalo_min", INTERVALO_DEFECTO_MIN)
    for error in (e1, e2, e3, e4):
        if error:
            return no(error)
    n_ops, cada = int(n_ops), int(cada)
    if riesgo <= 0:
        return no("El riesgo por operación debe ser mayor que 0.")
    if riesgo > ordenes.LIMITES.riesgo_max_por_operacion_pct:
        return no(f"El riesgo por operación ({riesgo}%) supera el máximo permitido "
                  f"({ordenes.LIMITES.riesgo_max_por_operacion_pct}%).")
    if not 1 <= n_ops <= MAX_OPERACIONES_TOPE:
        return no(f"El máximo de operaciones debe estar entre 1 y {MAX_OPERACIONES_TOPE}.")
    if not DURACION_MIN_H <= horas <= DURACION_MAX_H:
        return no(f"La duración debe estar entre {DURACION_MIN_H:g} y {DURACION_MAX_H:g} horas.")
    if not INTERVALO_MIN <= cada <= INTERVALO_MAX:
        return no(f"El intervalo de chequeo debe estar entre {INTERVALO_MIN} y {INTERVALO_MAX} minutos.")

    _, motivo = ordenes.cuenta_demo()
    if motivo:
        return no(motivo)
    val = ordenes.validar_simbolo(simbolo)
    if not val["ok"]:
        return no(val["motivo"])
    sym = val["simbolo"]

    _caducar_autorizaciones()
    vigentes = _consultar(
        "SELECT * FROM vigilancias WHERE usuario_id = ? AND estado IN ('PENDIENTE_AUTORIZACION', 'ACTIVA')",
        (usuario_id,),
    )
    for otra in vigentes:
        if otra["simbolo"].upper() == sym.upper():
            estado = "pendiente de tu autorización" if otra["estado"] == PENDIENTE else "activa"
            return no(f"Ya hay una vigilancia {estado} para {sym}. Detenla o resuélvela antes de crear otra.")
    if len(vigentes) >= MAX_VIGILANCIAS_POR_USUARIO:
        return no(f"Ya hay {len(vigentes)} vigilancias vigentes (máximo {MAX_VIGILANCIAS_POR_USUARIO}). "
                  "Detén alguna antes de crear otra.")

    ahora = datetime.now()
    vid = uuid.uuid4().hex[:8]
    ordenes._ejecutar(
        "INSERT INTO vigilancias (id, usuario_id, simbolo, estado, instruccion, creada, expira_autorizacion, "
        "duracion_horas, intervalo_min, riesgo_pct, max_operaciones, permite_cerrar) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
        (vid, usuario_id, sym, PENDIENTE, (instruccion or "").strip()[:500], _iso(ahora),
         _iso(ahora + timedelta(minutes=ordenes.LIMITES.vigencia_propuesta_min)), horas, cada, riesgo, n_ops),
    )
    return {"ok": True, "id": vid, "resumen": resumen_terminos(obtener(vid) or {})}


def autorizar(vid: str, usuario_id: str) -> dict[str, Any]:
    """El usuario autoriza la vigilancia (botón del panel). La activa y arranca el motor."""
    v = obtener(vid)
    if not v or v["usuario_id"] != usuario_id:
        return {"ok": False, "mensaje": "La vigilancia no existe."}
    _, motivo = ordenes.cuenta_demo()
    if motivo:
        return {"ok": False, "mensaje": motivo}
    ahora = datetime.now()
    reclamada = ordenes._ejecutar(
        "UPDATE vigilancias SET estado = 'ACTIVA', autorizada = ?, vence = ?, proximo_chequeo = ?, "
        "chequeos = 0, errores = 0 "
        "WHERE id = ? AND estado = 'PENDIENTE_AUTORIZACION' AND expira_autorizacion > ?",
        (_iso(ahora), _iso(ahora + timedelta(hours=float(v["duracion_horas"]))), _iso(ahora), vid, _iso(ahora)),
    )
    if reclamada == 0:
        if v["estado"] == PENDIENTE:
            _actualizar(vid, estado=EXPIRADA)
            return {"ok": False, "mensaje": "La autorización venció. Pídele al agente que la prepare de nuevo."}
        return {"ok": False, "mensaje": f"La vigilancia ya está en estado {v['estado']}."}
    iniciar_motor()
    return {"ok": True, "mensaje": f"Vigilancia de {v['simbolo']} activada. Te avisaré de cada operación."}


def rechazar(vid: str, usuario_id: str) -> bool:
    return ordenes._ejecutar(
        "UPDATE vigilancias SET estado = 'CANCELADA', detalle = 'No autorizada por el usuario' "
        "WHERE id = ? AND usuario_id = ? AND estado = 'PENDIENTE_AUTORIZACION'", (vid, usuario_id),
    ) == 1


def detener(usuario_id: str, vid: str | None = None, simbolo: str | None = None) -> dict[str, Any]:
    """Detiene (por id o por símbolo) las vigilancias vigentes del usuario. No cierra posiciones abiertas."""
    filas = _consultar(
        "SELECT * FROM vigilancias WHERE usuario_id = ? AND estado IN ('PENDIENTE_AUTORIZACION', 'ACTIVA')",
        (usuario_id,),
    )
    if vid:
        filas = [f for f in filas if f["id"] == vid]
    elif simbolo:
        real = ordenes._resolver_simbolo(simbolo).upper()
        filas = [f for f in filas if f["simbolo"].upper() in (real, ordenes._normalizar(simbolo))]
    if not filas:
        return {"ok": False, "mensaje": "No hay una vigilancia vigente que coincida."}
    detenidas, con_posicion = [], []
    for f in filas:
        ordenes._ejecutar(
            "UPDATE vigilancias SET estado = 'CANCELADA', detalle = 'Detenida por el usuario' WHERE id = ?", (f["id"],))
        detenidas.append(f["simbolo"])
        if f["estado"] == ACTIVA and _posiciones_de(f):
            con_posicion.append(f["simbolo"])
    mensaje = f"Vigilancia detenida: {', '.join(detenidas)}."
    if con_posicion:
        mensaje += (f" Ojo: queda una posición abierta en {', '.join(con_posicion)} "
                    "(sigue con su stop loss y take profit); ciérrala tú si lo prefieres.")
    return {"ok": True, "mensaje": mensaje, "detenidas": detenidas}


def listar(usuario_id: str, incluir_finalizadas: bool = False, limite: int = 10) -> list[dict[str, Any]]:
    """Vigilancias del usuario: las vigentes, y opcionalmente las últimas ya terminadas."""
    _caducar_autorizaciones()
    if incluir_finalizadas:
        return _consultar("SELECT * FROM vigilancias WHERE usuario_id = ? ORDER BY creada DESC, rowid DESC LIMIT ?",
                          (usuario_id, int(limite)))
    return _consultar(
        "SELECT * FROM vigilancias WHERE usuario_id = ? AND estado IN ('PENDIENTE_AUTORIZACION', 'ACTIVA') "
        "ORDER BY creada, rowid", (usuario_id,),
    )


# ══════════════════════════════════════════════════════════════
#  Posiciones de una vigilancia (solo las que ella abrió)
# ══════════════════════════════════════════════════════════════
def _posiciones_de(v: dict[str, Any]) -> list[Any]:
    ids = {f["id"] for f in _consultar(
        "SELECT id FROM ordenes WHERE vigilancia_id = ? AND accion = 'abrir' AND estado = 'EJECUTADA'", (v["id"],))}
    if not ids:
        return []
    with ordenes.MT5_LOCK:
        abiertas = mt5.positions_get(symbol=v["simbolo"]) or []
    return [p for p in abiertas if (getattr(p, "comment", "") or "").rpartition(":")[2] in ids]


# ══════════════════════════════════════════════════════════════
#  Decisión del modelo
# ══════════════════════════════════════════════════════════════
_RE_OBJETO = re.compile(r"\{[^{}]*\}", re.S)
_SINONIMOS = {
    "espera": "esperar", "esperar": "esperar", "wait": "esperar", "hold": "esperar", "mantener": "esperar",
    "abrir": "abrir", "open": "abrir", "comprar": "abrir", "vender": "abrir",
    "cerrar": "cerrar", "close": "cerrar",
}


def parsear_decision(texto: str) -> dict[str, Any]:
    """Lee el bloque ```decision {...}``` del final de la respuesta. Si no hay uno válido, la decisión es
    ESPERAR (nunca se opera por una respuesta que no se entiende)."""
    candidatos = []
    for m in _RE_OBJETO.finditer(texto or ""):
        if '"accion"' in m.group(0) or "'accion'" in m.group(0):
            candidatos.append(m.group(0))
    for crudo in reversed(candidatos):
        try:
            d = json.loads(crudo)
        except ValueError:
            continue
        if not isinstance(d, dict):
            continue
        accion = _SINONIMOS.get(str(d.get("accion", "")).strip().lower())
        if accion is None:
            continue
        lado = str(d.get("lado", "")).strip().lower()
        if str(d.get("accion", "")).strip().lower() == "comprar":
            lado = "compra"
        elif str(d.get("accion", "")).strip().lower() == "vender":
            lado = "venta"
        ticket = _a_numero(d.get("ticket"))
        return {
            "accion": accion,
            "lado": lado if lado in ("compra", "venta") else None,
            "stop_loss": _a_numero(d.get("stop_loss")),
            "take_profit": _a_numero(d.get("take_profit")),
            "ticket": int(ticket) if ticket is not None else None,
            "resumen": str(d.get("resumen") or "").strip()[:300],
        }
    return {"accion": "esperar", "lado": None, "stop_loss": None, "take_profit": None, "ticket": None,
            "resumen": "No se pudo leer la decisión del análisis; se espera al próximo chequeo.", "invalida": True}


# ══════════════════════════════════════════════════════════════
#  Agente del análisis (sin herramientas de ejecución)
# ══════════════════════════════════════════════════════════════
class _RegistroSinEjecucion:
    """Registro de herramientas para el análisis automático: el de siempre MENOS las que proponen o
    programan órdenes. Así el modelo no puede ejecutar nada por su cuenta; solo analiza y decide."""

    def __init__(self, base: Any, excluidas: frozenset = HERRAMIENTAS_EXCLUIDAS) -> None:
        self._base, self._excluidas = base, excluidas

    def nombres(self) -> list[str]:
        return [n for n in self._base.nombres() if n not in self._excluidas]

    def esquemas(self) -> list[dict[str, Any]]:
        return [e for e in self._base.esquemas() if e.get("function", {}).get("name") not in self._excluidas]

    def ejecutar(self, nombre: str, argumentos: dict[str, Any]) -> str:
        if nombre in self._excluidas:
            return json.dumps({"error": "Esa herramienta no está disponible en el análisis automático."}, ensure_ascii=False)
        return self._base.ejecutar(nombre, argumentos)


def _fabrica_agente_real() -> Any:
    from core.agente import Agente  # import tardío: evita ciclos y no carga el modelo si no hace falta
    from herramientas.base import REGISTRO
    # usuario_id=None: sin memoria persistente; cada chequeo es una conversación nueva y barata.
    return Agente(perfil=PERFIL_VIGILANCIA, registro=_RegistroSinEjecucion(REGISTRO), usuario_id=None)


# Se puede sustituir (las pruebas inyectan un agente falso).
fabrica_agente: Callable[[], Any] = _fabrica_agente_real


def _mensaje_analisis(v: dict[str, Any], posiciones: list[Any]) -> str:
    if posiciones:
        filas = []
        for p in posiciones:
            tipo = "compra" if p.type == mt5.POSITION_TYPE_BUY else "venta"
            filas.append(
                f"- ticket {p.ticket}: {tipo} {p.volume:g} lotes, abierta a {p.price_open}, ahora {p.price_current}, "
                f"SL {p.sl or 'sin SL'}, TP {p.tp or 'sin TP'}, resultado {p.profit:+.2f}"
            )
        abiertas = "\n".join(filas)
    else:
        abiertas = "- ninguna"
    puede_cerrar = "SÍ, solo las listadas arriba" if v.get("permite_cerrar") else "NO"
    return f"""MODO VIGILANCIA AUTOMÁTICA (el usuario te autorizó a operar solo este activo).

Activo: {v['simbolo']}
Lo que pidió el usuario: {v.get('instruccion') or '(vigilar el activo y operar en el mejor momento)'}
Hora local: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Chequeo número {int(v.get('chequeos') or 0)} (cada {v['intervalo_min']} min). Aperturas hechas: {v.get('operaciones') or 0} de {v['max_operaciones']}.
Riesgo por operación fijado por el sistema: {v['riesgo_pct']}% del equity (el lote lo calcula el sistema).
Posiciones abiertas por esta vigilancia:
{abiertas}
¿Puedes cerrarlas por tu análisis?: {puede_cerrar}
Último resumen tuyo: {v.get('ultimo_resumen') or '(primer chequeo)'}

Qué hacer:
1. Analiza {v['simbolo']} con las herramientas de datos (precio actual, velas en varios marcos de tiempo, niveles clave, tendencia, noticias próximas de alto impacto, etc.).
2. Decide UNA acción: esperar, abrir o cerrar. Esperar es una decisión válida y a menudo la mejor: abre solo si hay una oportunidad clara, con un stop loss lógico (obligatorio) y una relación beneficio/riesgo razonable. No abras si ya hay una posición abierta.
3. No existen herramientas para ejecutar: el sistema ejecutará tu decisión por ti, dentro de sus límites de riesgo.
4. Explica tu análisis en pocas líneas y termina SIEMPRE con este bloque (JSON válido, nada después):
```decision
{{"accion": "esperar", "resumen": "una frase para el historial"}}
```
Para abrir: {{"accion": "abrir", "lado": "compra" o "venta", "stop_loss": precio, "take_profit": precio, "resumen": "..."}}
Para cerrar una de las posiciones listadas: {{"accion": "cerrar", "ticket": número, "resumen": "..."}}"""


# ══════════════════════════════════════════════════════════════
#  Ejecución de la decisión (solo el motor ejecuta)
# ══════════════════════════════════════════════════════════════
def _aplicar(v: dict[str, Any], d: dict[str, Any], posiciones: list[Any]) -> str:
    """Valida y ejecuta la decisión. Devuelve el resumen para el historial de la vigilancia."""
    sym, resumen = v["simbolo"], d.get("resumen") or ""
    if d["accion"] == "abrir":
        if len(posiciones) >= MAX_ABIERTAS_POR_VIGILANCIA:
            return f"Esperar: ya hay una posición abierta. {resumen}".strip()
        if (v.get("operaciones") or 0) >= v["max_operaciones"]:
            return "Esperar: se alcanzó el máximo de operaciones de esta vigilancia."
        if d["lado"] is None or d["stop_loss"] is None:
            return "No se abrió: la decisión no traía un lado y un stop loss válidos."
        prop = ordenes.proponer_apertura(
            sym, d["lado"], d["stop_loss"], d["take_profit"], v["riesgo_pct"],
            resumen or "Operación automática de la vigilancia", origen="automatica", vigilancia_id=v["id"],
        )
        if prop.get("estado") != "PROPUESTA_PENDIENTE":
            motivo = prop.get("motivo") or prop.get("mensaje") or "bloqueada por los límites de riesgo"
            _notificar(v, f"Operación bloqueada · {sym}", f"El agente quiso abrir {d['lado']} pero: {motivo}", tipo="error")
            return f"Bloqueada: {motivo}"
        res = ordenes.confirmar_orden(prop["id"])
        if res.get("ok"):
            ordenes._ejecutar("UPDATE vigilancias SET operaciones = operaciones + 1 WHERE id = ?", (v["id"],))
            r = prop["resumen"]
            detalle = (f"{r['volumen']:g} lotes · SL {r['stop_loss']} · TP {r['take_profit'] or '—'} · "
                       f"riesgo {r['riesgo']}")
            _notificar(v, f"{_lado_txt(d['lado'])} automática · {sym}", f"{detalle}. {res.get('mensaje', '')}")
            return f"Abrió {d['lado']}: {resumen}".strip()
        _notificar(v, f"No se pudo ejecutar · {sym}", res.get("mensaje", "Error al enviar la orden."), tipo="error")
        return f"No se ejecutó: {res.get('mensaje', '')}"
    if d["accion"] == "cerrar":
        if not v.get("permite_cerrar"):
            return "No se cerró: esta vigilancia no tiene permiso para cerrar."
        propias = {int(p.ticket): p for p in posiciones}
        ticket = d["ticket"] if d["ticket"] is not None else (next(iter(propias)) if len(propias) == 1 else None)
        if ticket not in propias:
            return "No se cerró: el ticket no corresponde a una posición abierta por esta vigilancia."
        resultado_actual = propias[ticket].profit
        prop = ordenes.proponer_cierre(ticket, resumen or "Cierre automático de la vigilancia",
                                       origen="automatica", vigilancia_id=v["id"])
        if prop.get("estado") != "PROPUESTA_PENDIENTE":
            motivo = prop.get("motivo") or "no se pudo preparar el cierre"
            _notificar(v, f"No se pudo cerrar · {sym}", motivo, tipo="error")
            return f"No se cerró: {motivo}"
        res = ordenes.confirmar_orden(prop["id"])
        if res.get("ok"):
            _notificar(v, f"Posición cerrada · {sym}",
                       f"Resultado ≈ {resultado_actual:+.2f}. {resumen or res.get('mensaje', '')}".strip())
            return f"Cerró la posición #{ticket}: {resumen}".strip()
        _notificar(v, f"No se pudo cerrar · {sym}", res.get("mensaje", "Error al enviar la orden."), tipo="error")
        return f"No se cerró: {res.get('mensaje', '')}"
    return f"Esperar: {resumen}".strip()


# ══════════════════════════════════════════════════════════════
#  Chequeo de una vigilancia
# ══════════════════════════════════════════════════════════════
def _finalizar(v: dict[str, Any], estado: str, titulo: str, texto: str, tipo: str = "auto") -> None:
    _actualizar(v["id"], estado=estado, detalle=texto[:300])
    _notificar(v, titulo, texto, tipo=tipo)


def chequear(vid: str) -> dict[str, Any]:
    """Un chequeo: analiza el activo y, si el modelo lo decide, ejecuta. Lo lanza el motor."""
    v = obtener(vid)
    if not v or v["estado"] != ACTIVA:
        return {"ok": False, "motivo": "La vigilancia no está activa."}
    ahora = datetime.now()
    _actualizar(vid, ultimo_chequeo=_iso(ahora), chequeos=(v.get("chequeos") or 0) + 1,
                proximo_chequeo=_iso(ahora + timedelta(minutes=int(v["intervalo_min"]))))
    v = obtener(vid) or v

    cuenta, motivo = ordenes.cuenta_demo()
    if motivo and cuenta is not None:      # MT5 responde pero la cuenta NO es demo: se detiene todo
        _finalizar(v, ERROR, f"Vigilancia detenida · {v['simbolo']}", motivo, tipo="error")
        return {"ok": False, "motivo": motivo}
    if motivo:                              # MT5 sin conexión: se reintenta en el próximo chequeo
        _actualizar(vid, ultimo_resumen=f"Sin conexión con MetaTrader 5; se reintenta. ({motivo})"[:300])
        return {"ok": False, "motivo": motivo}

    posiciones = _posiciones_de(v)
    if (v.get("operaciones") or 0) >= v["max_operaciones"] and not posiciones:
        _finalizar(v, FINALIZADA, f"Vigilancia finalizada · {v['simbolo']}",
                   f"Se realizaron las {v['max_operaciones']} operaciones previstas y no queda ninguna posición abierta.")
        return {"ok": True, "estado": FINALIZADA}
    if ordenes.kill_switch_activo() and not posiciones:
        _actualizar(vid, ultimo_resumen="En pausa: el interruptor de emergencia bloquea las aperturas.")
        return {"ok": True, "estado": "EN_PAUSA"}

    with ordenes.MT5_LOCK:
        tick = mt5.symbol_info_tick(v["simbolo"])
    hora_tick = int(tick.time) if tick is not None and getattr(tick, "time", 0) else None
    if hora_tick is not None and v.get("ultimo_tick") == hora_tick:   # nada se movió: no se gastan tokens
        _actualizar(vid, ultimo_resumen="Mercado sin movimiento desde el último chequeo: no se analizó.")
        return {"ok": True, "estado": "SIN_MOVIMIENTO"}

    try:
        texto = fabrica_agente().responder(_mensaje_analisis(v, posiciones))
    except Exception as e:  # noqa: BLE001 - el fallo del modelo no debe tumbar el motor
        errores = (v.get("errores") or 0) + 1
        _actualizar(vid, errores=errores, ultimo_resumen=f"Falló el análisis: {e}"[:300])
        if errores >= ERRORES_SEGUIDOS_MAX:
            _finalizar(v, ERROR, f"Vigilancia detenida · {v['simbolo']}",
                       f"El análisis falló {errores} veces seguidas: {e}", tipo="error")
        return {"ok": False, "motivo": str(e)}

    actual = obtener(vid)
    if not actual or actual["estado"] != ACTIVA:   # el usuario la detuvo mientras el modelo pensaba
        return {"ok": False, "motivo": "La vigilancia fue detenida durante el análisis; se descartó la decisión."}
    decision = parsear_decision(texto)
    resumen = _aplicar(actual, decision, _posiciones_de(actual))
    _actualizar(vid, errores=0, ultimo_tick=hora_tick, ultimo_resumen=f"{ahora:%H:%M} · {resumen}"[:300])
    return {"ok": True, "decision": decision, "resumen": resumen}


# ══════════════════════════════════════════════════════════════
#  Motor en segundo plano
# ══════════════════════════════════════════════════════════════
def _caducar_autorizaciones() -> None:
    ordenes._ejecutar(
        "UPDATE vigilancias SET estado = 'EXPIRADA', detalle = 'La autorización venció' "
        "WHERE estado = 'PENDIENTE_AUTORIZACION' AND expira_autorizacion <= ?", (ordenes._ahora(),),
    )


def _caducar_vencidas() -> None:
    for v in _consultar("SELECT * FROM vigilancias WHERE estado = 'ACTIVA' AND vence <= ?", (ordenes._ahora(),)):
        extra = " Queda una posición abierta (con su stop loss y take profit)." if _posiciones_de(v) else ""
        _finalizar(v, EXPIRADA, f"Vigilancia terminada · {v['simbolo']}",
                   f"Se cumplió el tiempo de la vigilancia ({v['duracion_horas']:g} h).{extra}")


def _chequeo_en_curso(vid: str) -> bool:
    nombre = f"{PREFIJO_HILO_CHEQUEO}{vid}"
    return any(t.name == nombre and t.is_alive() for t in threading.enumerate())


def _chequear_seguro(vid: str) -> None:
    try:
        chequear(vid)
    except Exception:  # noqa: BLE001
        traceback.print_exc()


def tick(sincrono: bool = False) -> int:
    """Una pasada del motor: caduca lo vencido y lanza los chequeos que ya tocan. Devuelve cuántos lanzó."""
    _caducar_autorizaciones()
    _caducar_vencidas()
    toca = _consultar(
        "SELECT id FROM vigilancias WHERE estado = 'ACTIVA' AND (proximo_chequeo IS NULL OR proximo_chequeo <= ?)",
        (ordenes._ahora(),),
    )
    lanzados = 0
    for fila in toca:
        vid = fila["id"]
        if _chequeo_en_curso(vid):
            continue
        if sincrono:
            _chequear_seguro(vid)
        else:
            threading.Thread(target=_chequear_seguro, args=(vid,), name=f"{PREFIJO_HILO_CHEQUEO}{vid}",
                             daemon=True).start()
        lanzados += 1
    return lanzados


def _bucle() -> None:
    while True:
        try:
            tick()
        except Exception:  # noqa: BLE001
            traceback.print_exc()
        time.sleep(ESPERA_MOTOR_S)


_LOCK_MOTOR = threading.Lock()


def iniciar_motor() -> bool:
    """Arranca el motor si no está ya en marcha (idempotente, también si Streamlit recarga el módulo).
    Devuelve True si lo arrancó ahora."""
    with _LOCK_MOTOR:
        if any(t.name == NOMBRE_HILO_MOTOR and t.is_alive() for t in threading.enumerate()):
            return False
        threading.Thread(target=_bucle, name=NOMBRE_HILO_MOTOR, daemon=True).start()
        return True
