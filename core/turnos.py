"""Turnos del agente en segundo plano.

NOMBRE DEL ARCHIVO: core/turnos.py

Problema que resuelve: Streamlit vuelve a ejecutar el script entero cada vez que el usuario hace
algo (cambiar de sección, pulsar un botón...). Si el agente corría DENTRO de esa ejecución, cualquier
clic lo cortaba a mitad de la respuesta.

Solución: el turno del agente corre en un hilo propio (daemon). La interfaz solo lo consulta:
  * iniciar()   -> lanza el hilo con la pregunta del usuario (un turno a la vez por usuario).
  * turno_de()  -> estado actual: texto parcial, herramientas usadas, tiempo transcurrido...
  * recoger()   -> la interfaz ya mostró el resultado; el turno deja de estar "pendiente".
Al terminar, el hilo deja un aviso en core/notificaciones.py (la campana de la barra superior).

Detener (cancelar): un hilo no se puede matar a la fuerza a mitad de una llamada, así que cancelar()
solo PIDE la parada; el hilo la atiende en cuanto el agente emite su siguiente evento (al escribir,
casi al instante; si está dentro de una herramienta o esperando al modelo, al terminar esa llamada).
Al detenerlo se cierra el generador del agente, que descarta el turno incompleto de su historial: las
consultas siguientes no arrastran la cancelada.

Este módulo NO usa Streamlit: lo ejecuta un hilo sin contexto de la app. Las herramientas del
agente que hablan con MT5 ya serializan el acceso con MT5_LOCK, igual que antes.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from core import notificaciones

_EXT_IMAGEN = (".png", ".jpg", ".jpeg", ".webp")
VISTA_RECIENTE_S = 2.0   # la interfaz late cada 1 s: si lo mostró hace menos de esto, el usuario lo está viendo


# ── Utilidades ────────────────────────────────────────────────────────────────────────
def _buscar_rutas_imagen(dato: Any, rutas: list) -> None:
    """Busca de forma recursiva el campo 'archivo_guardado' (imagen en disco) en un resultado."""
    if isinstance(dato, dict):
        ruta = dato.get("archivo_guardado")
        if isinstance(ruta, str) and ruta.lower().endswith(_EXT_IMAGEN) and os.path.isfile(ruta):
            if ruta not in rutas:
                rutas.append(ruta)
        for valor in dato.values():
            if isinstance(valor, (dict, list)):
                _buscar_rutas_imagen(valor, rutas)
    elif isinstance(dato, list):
        for valor in dato:
            _buscar_rutas_imagen(valor, rutas)


def imagenes_de_resultado(resultado: Any) -> list:
    """Imágenes que una herramienta guardó en disco, a partir de su resultado (JSON o dict)."""
    try:
        datos = json.loads(resultado) if isinstance(resultado, str) else resultado
    except (TypeError, ValueError):
        return []
    rutas: list = []
    _buscar_rutas_imagen(datos, rutas)
    return rutas


def formatear_duracion(segundos: float) -> str:
    """'7 s', '1 min 12 s'..."""
    s = max(0, int(segundos))
    return f"{s} s" if s < 60 else f"{s // 60} min {s % 60:02d} s"


def formatear_reloj(segundos: float) -> str:
    """'00:07', '01:12' (para el cronómetro en vivo)."""
    s = max(0, int(segundos))
    return f"{s // 60:02d}:{s % 60:02d}"


# ── Turno ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Turno:
    usuario_id: str
    prompt: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    terminado: bool = False
    recogido: bool = False           # la interfaz ya incorporó el resultado al chat
    fase: str = "Pensando…"          # texto corto de lo que está haciendo ahora mismo
    texto: str = ""                  # respuesta acumulada (se va llenando mientras llega)
    herramientas: list = field(default_factory=list)
    imagenes: list = field(default_factory=list)
    hubo_orden: bool = False         # el agente llamó a proponer_orden / proponer_cierre_posicion
    error: str = ""
    tokens_entrada: Any = "?"
    tokens_salida: Any = "?"
    perfil: Any = "?"
    t_inicio: float = field(default_factory=time.time)
    t_fin: float | None = None
    ui_viva: float = 0.0             # última vez que la interfaz estaba mostrando este turno
    cancelar_solicitado: bool = False  # el usuario pulsó "Detener" (el hilo aún puede estar terminando)
    cancelado: bool = False          # el turno se interrumpió de verdad antes de terminar solo

    @property
    def duracion(self) -> float:
        return (self.t_fin or time.time()) - self.t_inicio

    @property
    def pie(self) -> str:
        if self.cancelado:
            return f"⏹ Detenida a los {formatear_duracion(self.duracion)}"
        return (
            f"⏱ {formatear_duracion(self.duracion)} · {self.tokens_entrada} entrada / "
            f"{self.tokens_salida} salida | perfil: {self.perfil}"
        )

    def respuesta_final(self) -> str:
        """Texto que se guarda en el chat (con el mismo criterio de antes si no hubo texto)."""
        texto = self.texto
        if self.cancelado:
            nota = "⏹ **Consulta detenida por el usuario.**"
            if self.hubo_orden:
                nota += (" El agente ya había propuesto una orden: revísala en «Órdenes propuestas» y "
                         "confírmala o recházala.")
            return f"{texto.rstrip()}\n\n{nota}" if texto.strip() else nota
        if self.error:
            texto += f"\n\n⚠️ {self.error}"
        if not texto.strip():
            texto = "(Sin texto adicional del agente.)" if self.imagenes else "(El agente no devolvió texto.)"
        return texto


_LOCK = threading.Lock()
_TURNOS: dict[str, Turno] = {}    # último turno de cada usuario
_AGENTES: dict[str, Any] = {}     # un Agente por usuario (sobrevive a recargas de la página)


# ── API ───────────────────────────────────────────────────────────────────────────────
def agente_de(usuario_id: str) -> Any:
    with _LOCK:
        return _AGENTES.get(usuario_id)


def registrar_agente(usuario_id: str, agente: Any) -> None:
    with _LOCK:
        _AGENTES[usuario_id] = agente


def turno_de(usuario_id: str) -> Turno | None:
    with _LOCK:
        return _TURNOS.get(usuario_id)


def hay_turno_en_curso(usuario_id: str) -> bool:
    t = turno_de(usuario_id)
    return t is not None and not t.terminado


def iniciar(usuario_id: str, agente: Any, prompt: str) -> Turno | None:
    """Lanza el turno en segundo plano. Devuelve None si ya hay uno en curso para ese usuario."""
    with _LOCK:
        actual = _TURNOS.get(usuario_id)
        if actual is not None and not actual.terminado:
            return None
        turno = Turno(usuario_id=usuario_id, prompt=prompt)
        _TURNOS[usuario_id] = turno
    threading.Thread(target=_correr, args=(turno, agente), name=f"turno-{turno.id}", daemon=True).start()
    return turno


def cancelar(usuario_id: str) -> bool:
    """Pide detener el turno en curso del usuario. True si había uno al que pedírselo."""
    with _LOCK:
        t = _TURNOS.get(usuario_id)
        if t is None or t.terminado:
            return False
        t.cancelar_solicitado = True
        t.fase = "Deteniendo…"
        return True


def recoger(usuario_id: str, turno_id: str) -> None:
    """La interfaz ya mostró el resultado: se marca como incorporado y se leen sus avisos."""
    with _LOCK:
        t = _TURNOS.get(usuario_id)
        if t is not None and t.id == turno_id:
            t.recogido = True
    notificaciones.marcar_leidas(usuario_id, ref=turno_id)


# ── Hilo ──────────────────────────────────────────────────────────────────────────────
def _correr(turno: Turno, agente: Any) -> None:
    gen = agente.responder_stream(turno.prompt)
    try:
        for ev in gen:
            if turno.cancelar_solicitado:
                turno.cancelado = True
                break
            if ev.tipo == "razonamiento":
                turno.fase = "Analizando…"
            elif ev.tipo == "texto":
                turno.fase = "Redactando la respuesta…"
                turno.texto += ev.texto
            elif ev.tipo == "herramienta":
                # El usuario no ve qué herramienta se usa: solo una fase genérica (el nombre queda en
                # turno.herramientas por si hace falta depurar, pero la interfaz no lo muestra).
                turno.fase = ("Preparando la propuesta…" if str(ev.texto).startswith("proponer_")
                              else "Consultando los datos…")
                turno.herramientas.append(str(ev.texto))
            elif ev.tipo == "resultado":
                turno.fase = "Procesando los datos…"
                if ev.texto in ("proponer_orden", "proponer_cierre_posicion"):
                    turno.hubo_orden = True
                for ruta in imagenes_de_resultado((ev.datos or {}).get("resultado")):
                    if ruta not in turno.imagenes:
                        turno.imagenes.append(ruta)
            elif ev.tipo == "fin":
                d = ev.datos or {}
                turno.tokens_entrada = d.get("tokens_entrada", "?")
                turno.tokens_salida = d.get("tokens_salida", "?")
                turno.perfil = d.get("perfil", "?")
    except Exception as e:  # noqa: BLE001 - el error se muestra en el chat, no se pierde en el hilo
        if not turno.cancelar_solicitado:   # si el usuario ya lo había detenido, el fallo no importa
            motivo = "Error del modelo" if type(e).__name__ == "ErrorLLM" else "Error al ejecutar el agente"
            turno.error = f"{motivo}: {e}"
    finally:
        try:
            gen.close()   # si se detuvo a medias, el agente descarta ese turno incompleto de su historial
        except Exception:  # noqa: BLE001
            pass
        turno.t_fin = time.time()
        try:
            if not turno.cancelado:   # lo detuvo el propio usuario: no hace falta avisarle
                _avisar(turno)
        finally:
            turno.terminado = True   # al final: así la interfaz ya encuentra el aviso creado


def _avisar(turno: Turno) -> None:
    """Deja el aviso en la campana. Si el usuario está viendo el chat, nace ya leído."""
    viendo = (time.time() - turno.ui_viva) < VISTA_RECIENTE_S
    pregunta = turno.prompt if len(turno.prompt) <= 80 else turno.prompt[:77] + "…"
    tiempo = formatear_duracion(turno.duracion)
    if turno.error:
        titulo, tipo = "El agente no pudo responder", "error"
    elif turno.hubo_orden:
        titulo, tipo = "El agente propuso una orden", "orden"
    else:
        titulo, tipo = "El agente respondió", "agente"
    notificaciones.agregar(
        turno.usuario_id, titulo, f"{pregunta} · {tiempo}", tipo=tipo, ref=turno.id, leida=viendo,
    )
