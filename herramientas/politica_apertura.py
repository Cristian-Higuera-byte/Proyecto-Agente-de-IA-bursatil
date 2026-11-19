# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ----------------------------- INICIO Piña y Jara politica_apertura .PY --------------------------------
# -------------------------------------------------------------------------------------------------------

"""
politica_apertura.py
--------------------
Política ÚNICA de apertura de operaciones.

Toda orden que abre exposición (mercado, pendiente nueva o cambio de precio de una pendiente) pasa por `motivo_de_bloqueo()` justo antes de salir hacia el bróker, sin importar por
qué camino llegó: el gráfico y el ticket, el agente de IA, las vigilancias automáticas o el copy trading. La comprobación vive en el propio conector de Capital.com
(herramientas/backends/capital_nucleo.py y mt5.py), no en cada pantalla ni en cada ruta HTTP, para que ninguna ruta nueva pueda saltársela.

Se rechaza abrir cuando:
  1. el operador activó la parada global;
  2. no hay un usuario identificado (sesión caída o hilo sin contexto);
  3. el usuario activó su parada de emergencia en esa cuenta;
  4. la cuenta es la real y la operación en cuenta real no está habilitada (`OPERAR_EN_CUENTA_REAL`, apagada por defecto);
  5. las credenciales de Capital.com con que corre este proceso ya no son las vigentes en la base (el usuario las reemplazó o las quitó), o no se puede verificar (V18 de la auditoría).

NO se aplica a lo que reduce o protege exposición: cerrar posiciones, cancelar órdenes pendientes y mover stop loss o take profit.
"""
import configuracion
from herramientas import paradas_emergencia


# TITULO MOTIVO DE BLOQUEO

def motivo_de_bloqueo(credenciales: tuple | None = None) -> str | None:
    """Texto con el motivo por el que NO se puede abrir ahora, o None si se puede. Usa el usuario y la cuenta de la sesión actual.

    `credenciales` es (clave del registro, versión) de la copia del conector que va a enviar la orden: si se indica, se verifica con la base (sin caché) que esas credenciales sigan vigentes. Lo
    pasa el conector justo antes de abrir; las demás consultas (por ejemplo, saber si hay un bloqueo para avisar en pantalla) no lo piden y no tocan la base."""
    if paradas_emergencia.activa_global():
        return "Las aperturas están bloqueadas por el operador de la plataforma."
    dueno = paradas_emergencia.dueno_actual()
    if dueno is None:
        return "No hay una sesión de usuario identificada: no se pueden abrir operaciones."
    if paradas_emergencia.activa_usuario():
        return "Las nuevas aperturas están bloqueadas (interruptor de emergencia activado por el usuario)."
    if dueno[1] == "real" and not configuracion.OPERAR_EN_CUENTA_REAL:
        return "La operación en cuenta real está deshabilitada en esta plataforma. Usa la cuenta demo."
    if credenciales is not None:
        from herramientas.backends import sesiones_capital          # se importa aquí para evitar un ciclo (el registro de sesiones carga el conector)
        return sesiones_capital.motivo_credenciales_no_vigentes(*credenciales)
    return None


# -------------------------------------------------------------------------------------------------------
# ------------------------------ FIN Piña y Jara politica_apertura .PY ----------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
