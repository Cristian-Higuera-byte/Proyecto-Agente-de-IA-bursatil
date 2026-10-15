"""Hilo que corre al agente: traduce sus eventos al estado del turno (fase, texto, herramientas, imágenes…)."""
from __future__ import annotations

import time
from typing import Any

from nucleo_agente import contexto
from nucleo_agente.turnos.avisos import _avisar
from nucleo_agente.turnos.imagenes import imagenes_de_resultado
from nucleo_agente.turnos.turno import Turno


def _correr(turno: Turno, agente: Any) -> None:
    contexto.fijar_usuario(turno.usuario_id)   # las herramientas que lo necesiten saben quién pregunta
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
                elif ev.texto == "proponer_vigilancia" and "VIGILANCIA_PENDIENTE" in str((ev.datos or {}).get("resultado", "")):
                    turno.hubo_vigilancia = True
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
