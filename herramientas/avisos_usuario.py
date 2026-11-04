# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# --------------------------------- INICIO Piña y Jara avisos_usuario .PY -------------------------------
# -------------------------------------------------------------------------------------------------------

"""Avisos de la campana que nacen de lo que pasa en la cuenta: cierres de posiciones y alertas de precio.

NOMBRE DEL ARCHIVO: herramientas/avisos_usuario.py

`revisar(usuario_id)` lo llama el vigilante de la campana (componentes_plataforma/barra_superior/notificaciones.py) cada pocos
segundos mientras el usuario tiene la plataforma abierta. Como la campana vive en el proceso de Streamlit, los avisos se generan
aquí y no en el servidor de precios (otro proceso). Cada cuenta (usuario y modo demo o real) recuerda sus posiciones conocidas.

Una posición cuenta como cerrada solo si falta en dos revisiones seguidas (separadas por al menos CONFIRMACION segundos): así una
lectura vacía por un fallo momentáneo de la red del bróker no genera avisos falsos.
"""
import threading
import time
import traceback
from typing import Any

from herramientas import gestor_alertas, gestor_lista_activos
from herramientas.backends import sesiones_capital
from herramientas.puente_mt5 import obtener_historial, obtener_info_cuenta, obtener_posiciones
from nucleo_agente import notificaciones

# Segundos mínimos entre dos revisiones de la misma cuenta (varias pestañas abiertas no multiplican las consultas).
INTERVALO = 10.0
# Segundos que una posición debe llevar ausente para darla por cerrada.
CONFIRMACION = 8.0
# Distancia relativa al nivel de SL o TP bajo la cual el último precio visto se considera «el nivel alcanzado».
TOLERANCIA_NIVEL = 0.003
# Candado y estado por cuenta: clave -> {"conocidas": {ticket: posición}, "ausentes": {ticket: instante}, "ultima": instante}.
_CANDADO = threading.Lock()
_ESTADO: dict[tuple, dict[str, Any]] = {}


# TITULO REVISAR

def revisar(usuario_id: str) -> None:
    """Revisa las posiciones y las alertas de precio de la cuenta actual y deja los avisos que correspondan en la campana.

    Se ignora si la cuenta se revisó hace menos de INTERVALO segundos. Cualquier fallo se imprime y se descarta: un aviso
    nunca debe romper la página."""
    ahora = time.time()
    with _CANDADO:
        estado = _ESTADO.setdefault(sesiones_capital.clave_actual(), {"conocidas": {}, "ausentes": {}, "ultima": 0.0})
        if ahora - estado["ultima"] < INTERVALO:
            return
        estado["ultima"] = ahora
    try:
        _revisar_posiciones(usuario_id, estado, ahora)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
    try:
        gestor_alertas.revisar_alertas(usuario_id)
    except Exception:  # noqa: BLE001
        traceback.print_exc()


# TITULO REVISAR POSICIONES

def _revisar_posiciones(usuario_id: str, estado: dict[str, Any], ahora: float) -> None:
    """Compara las posiciones abiertas con las conocidas y avisa de las que se cerraron.

    La primera revisión de una cuenta solo memoriza las posiciones (no avisa de nada). Si de golpe desaparecen todas y había
    más de una, se asume un fallo momentáneo del bróker y no se avisa."""
    actuales = {p["ticket"]: p for p in obtener_posiciones()}
    conocidas, ausentes = estado["conocidas"], estado["ausentes"]
    if not actuales and len(conocidas) > 1:
        return
    for ticket in [t for t in ausentes if t in actuales]:
        ausentes.pop(ticket)
    cerradas = []
    for ticket, posicion in conocidas.items():
        if ticket in actuales:
            continue
        if ahora - ausentes.setdefault(ticket, ahora) >= CONFIRMACION:
            cerradas.append(posicion)
    for posicion in cerradas:
        conocidas.pop(posicion["ticket"], None)
        ausentes.pop(posicion["ticket"], None)
        _avisar_cierre(usuario_id, posicion)
    conocidas.update(actuales)


# TITULO MOTIVO

def _motivo(posicion: dict[str, Any]) -> str | None:
    """«Stop loss» o «Take profit» si el último precio visto estaba sobre ese nivel de la posición; None si no (cierre manual u otro)."""
    precio = float(posicion.get("precio_actual") or 0.0)
    for nivel, nombre in ((posicion.get("sl"), "Stop loss"), (posicion.get("tp"), "Take profit")):
        nivel = float(nivel or 0.0)
        if nivel and precio and abs(precio - nivel) / nivel <= TOLERANCIA_NIVEL:
            return nombre
    return None


# TITULO RESULTADO

def _resultado(posicion: dict[str, Any]) -> tuple[float, bool]:
    """Ganancia o pérdida de la posición cerrada y si es exacta: la del historial del bróker, o la última vista (aproximada)."""
    try:
        for cierre in obtener_historial(dias=1, limite=80):
            if (cierre.get("symbol") == posicion.get("symbol") and cierre.get("pg") is not None
                    and abs(float(cierre.get("volumen", 0)) - float(posicion.get("volumen", 0))) < 1e-6):
                return float(cierre["pg"]), True
    except Exception:  # noqa: BLE001 - sin historial se usa la última ganancia vista
        pass
    return float(posicion.get("profit", 0.0) or 0.0), False


# TITULO AVISAR CIERRE

def _avisar_cierre(usuario_id: str, posicion: dict[str, Any]) -> None:
    """Deja en la campana el aviso de una posición cerrada: motivo (SL, TP o cierre), activo, lado, lotes y resultado."""
    ganancia, exacta = _resultado(posicion)
    try:
        moneda = obtener_info_cuenta().get("currency", "")
    except Exception:  # noqa: BLE001
        moneda = ""
    nombre = gestor_lista_activos.nombre_visible(posicion.get("symbol", ""))
    motivo = _motivo(posicion)
    titulo = f"{motivo} alcanzado · {nombre}" if motivo else f"Posición cerrada · {nombre}"
    texto = (f"{posicion.get('tipo', '')} {float(posicion.get('volumen', 0)):g} lotes · "
             f"{'P/G' if exacta else 'P/G aprox.'} {ganancia:+,.2f} {moneda}".strip())
    notificaciones.agregar(usuario_id, titulo, texto, tipo="posicion", categoria="posiciones")


# -------------------------------------------------------------------------------------------------------
# ---------------------------------- FIN Piña y Jara avisos_usuario .PY ---------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
