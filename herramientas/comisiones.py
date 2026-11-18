# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ---------------------------------- INICIO Piña y Jara comisiones .PY ----------------------------------
# -------------------------------------------------------------------------------------------------------

"""Comisión de rendimiento del copy trading: cuánto debe pagar el seguidor al gestor y el cobro con la billetera virtual.

Reglas:
  - La comisión es un porcentaje (el de la estrategia, entre 0 y 30 %) de la GANANCIA NUEVA de la copia: la suma de los resultados de sus operaciones, por encima de su
    marca de agua. La marca de agua (`copias.marca_agua`) es la mayor ganancia sobre la que ya se cobró; así nunca se cobra dos veces la misma ganancia, ni hay comisión
    mientras la copia no recupere sus pérdidas.
  - Se liquida cada `liquidacion_dias` días (30) desde el alta o desde la liquidación anterior, y una vez más al detener la copia (cuando ya no tiene posiciones abiertas
    o pasaron 10 minutos).
  - Atomicidad (V15 de la auditoría): cada liquidación tiene un FIN CANÓNICO que no depende de la hora en que corre cada trabajador (el corte anterior + `liquidacion_dias`, o la hora de cierre
    de la copia en la liquidación final). La liquidación se hace en la función SQL `comision_liquidar`, que bloquea la copia, calcula con la marca de agua vigente, guarda la liquidación (única
    por copia y fin de período) y ADELANTA la marca de agua en la misma operación: dos trabajadores sobre la misma copia y período producen una sola liquidación, y una comisión pendiente de
    cobro no se vuelve a calcular.
  - El pago pasa dinero de la billetera virtual del seguidor a la del gestor en una sola operación (`billetera.transferir`) con una clave derivada de la identidad de la liquidación
    (copia + fin del período): repetir no duplica.
    Si el seguidor no tiene saldo, la comisión queda pendiente, la copia se pausa (motivo `comision_pendiente`) y el motor reintenta en cada pasada; al cobrarse se reanuda sola.
  - Cada liquidación queda en `comisiones_rendimiento` (ganancia, marca de agua antes y después, porcentaje, comisión y el movimiento de billetera con el que se pagó).
Limitación: las posiciones que el seguidor deja abiertas al detener la copia no entran en la comisión final; lo que cierren después ya no se liquida.
"""
from datetime import datetime, timedelta, timezone

import configuracion
from herramientas import billetera

_TABLA = "comisiones_rendimiento"
# Minutos que se espera a que se cierren las posiciones de una copia detenida antes de liquidar su comisión final
_ESPERA_FINAL_MIN = 10


# TITULO AHORA

def _ahora() -> datetime:
    """Fecha y hora actual en UTC."""
    return datetime.now(timezone.utc)


# TITULO A FECHA

def _fecha(valor) -> datetime | None:
    """Convierte un texto ISO de Supabase en datetime con zona horaria; None si no se puede."""
    try:
        f = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        return f if f.tzinfo else f.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


# TITULO A NUMERO

def _n(valor, defecto: float = 0.0) -> float:
    """Convierte a número (Supabase puede entregar los numéricos como texto); `defecto` si está vacío o es inválido."""
    try:
        return float(valor)
    except (TypeError, ValueError):
        return defecto


# TITULO CALCULAR

def calcular(ganancia: float, marca_agua: float, porcentaje: float) -> tuple:
    """Devuelve (ganancia nueva, comisión): la parte de `ganancia` que supera la `marca_agua` y el `porcentaje` % de ella redondeado a centavos. (0, 0) si no la supera."""
    base = max(0.0, ganancia - marca_agua)
    return round(base, 2), round(base * porcentaje / 100.0, 2)


# TITULO GANANCIA DE LA COPIA

def ganancia_de(cliente, copia_id) -> float:
    """Ganancia acumulada de la copia: suma de los resultados de sus operaciones que ya tienen resultado (cerradas)."""
    filas = cliente.table("operaciones").select("resultado").eq("copia_id", copia_id).execute().data or []
    return round(sum(_n(f["resultado"]) for f in filas if f.get("resultado") is not None), 2)


# TITULO PENDIENTE

def pendiente(cliente, copia_id) -> float:
    """Total de comisiones de la copia que todavía no se cobraron."""
    filas = cliente.table(_TABLA).select("comision,movimiento_billetera_id").eq("copia_id", copia_id).execute().data or []
    return round(sum(_n(f["comision"]) for f in filas if f.get("movimiento_billetera_id") is None and _n(f["comision"]) > 0), 2)


# TITULO PAGAR

def _pagar(cliente, copia: dict, estrategia: dict, fila: dict) -> bool:
    """Intenta cobrar la comisión de la liquidación `fila` pasando el dinero de la billetera del seguidor a la del gestor. Devuelve True si quedó cobrada."""
    try:
        # La clave sale de la identidad de la liquidación (copia + fin del período); las liquidaciones anteriores a V15 no la tienen y usan la antigua, por id
        movimiento = billetera.transferir(copia["inversor_id"], estrategia["gestor_id"], _n(fila["comision"]), f"Comisión de rendimiento · {estrategia['nombre']}",
                                          f"Comisión de rendimiento · {estrategia['nombre']}", referencia=str(copia["id"]), clave_unica=fila.get("clave_pago") or f"comision-{fila['id']}")
    except billetera.ErrorBilletera:
        return False
    cliente.table(_TABLA).update({"movimiento_billetera_id": movimiento}).eq("id", fila["id"]).execute()
    cliente.table("copias").update({"marca_agua": max(_n(copia.get("marca_agua")), _n(fila["marca_agua_despues"]))}).eq("id", copia["id"]).execute()
    copia["marca_agua"] = max(_n(copia.get("marca_agua")), _n(fila["marca_agua_despues"]))
    return True


# TITULO COBRAR PENDIENTES

def cobrar_pendientes(cliente, copia: dict, estrategia: dict) -> float:
    """Intenta cobrar las comisiones pendientes de la copia. Si ya no queda nada pendiente y la copia estaba pausada por eso, la reanuda. Devuelve lo que sigue pendiente."""
    filas = cliente.table(_TABLA).select("*").eq("copia_id", copia["id"]).order("id").execute().data or []
    for f in filas:
        if f.get("movimiento_billetera_id") is None and _n(f["comision"]) > 0:
            _pagar(cliente, copia, estrategia, f)
    queda = pendiente(cliente, copia["id"])
    if queda <= 0 and copia.get("estado") == "pausada" and copia.get("motivo_cierre") == "comision_pendiente":
        cliente.table("copias").update({"estado": "activa", "motivo_cierre": None}).eq("id", copia["id"]).execute()
        copia.update({"estado": "activa", "motivo_cierre": None})
    return queda


# TITULO ULTIMO PERIODO

def _ultimo_corte(cliente, copia: dict) -> datetime:
    """Fecha desde la que corre el periodo actual: la de la última liquidación o, si no hay, la del alta de la copia."""
    fila = (cliente.table(_TABLA).select("periodo_hasta").eq("copia_id", copia["id"]).order("periodo_hasta", desc=True).limit(1).execute().data or [None])[0]
    return (_fecha(fila["periodo_hasta"]) if fila else None) or _fecha(copia.get("creada_en")) or _ahora()


# TITULO PERIODO A LIQUIDAR

def _periodo_a_liquidar(cliente, copia: dict, ahora: datetime) -> datetime | None:
    """Fin CANÓNICO del período que le toca liquidar a la copia, o None si no le toca ninguno.

    Es el mismo valor para cualquier trabajador y a cualquier hora: el corte anterior + `liquidacion_dias` días (liquidación mensual) o la hora de cierre de la copia (liquidación final, una
    vez que no tiene posiciones abiertas o pasaron `_ESPERA_FINAL_MIN` minutos). Así dos trabajadores que corren con horas distintas piden exactamente el mismo período y la base lo liquida una sola vez."""
    if copia["estado"] == "cerrada":
        if copia.get("comision_final_en"):
            return None
        cerrada = _fecha(copia.get("cerrada_en")) or ahora
        abiertas = cliente.table("operaciones").select("id").eq("copia_id", copia["id"]).eq("estado", "abierta").limit(1).execute().data or []
        return cerrada if (not abiertas or ahora >= cerrada + timedelta(minutes=_ESPERA_FINAL_MIN)) else None
    plazo = timedelta(days=configuracion.COPYTRADING["liquidacion_dias"])
    corte = _ultimo_corte(cliente, copia)
    return corte + plazo if ahora - corte >= plazo else None


# TITULO LIQUIDAR

def _liquidar(cliente, copia: dict, hasta: datetime, final: bool) -> dict | None:
    """Liquida el período que termina en `hasta` con la función SQL `comision_liquidar` (atómica: bloquea la copia, calcula, guarda y adelanta la marca de agua).

    Devuelve {"id", "nueva", "comision", "marca_agua_despues", "clave_pago", "movimiento_billetera_id"}, con `nueva` falso si otro trabajador ya liquidó ese período, o None si no había nada que
    liquidar. Si la función no existe o falla lanza la excepción: sin liquidación atómica NO se cobra nada."""
    filas = cliente.rpc("comision_liquidar", {"p_copia": int(copia["id"]), "p_hasta": hasta.isoformat(), "p_final": bool(final)}).execute().data or []
    if not filas:
        return None
    f = filas[0]
    return {"id": f["out_id"], "nueva": bool(f["out_nueva"]), "comision": _n(f["out_comision"]), "marca_agua_despues": _n(f["out_marca_despues"]),
            "clave_pago": f.get("out_clave_pago"), "movimiento_billetera_id": f.get("out_movimiento_id")}


# TITULO REVISAR

def revisar(cliente, copia: dict, estrategia: dict, ahora: datetime | None = None) -> dict:
    """Revisa la comisión de una copia: cobra lo pendiente y, si toca, hace la liquidación (mensual o final) y la cobra.

    Devuelve {"liquidada": bool, "comision": lo liquidado ahora, "pendiente": lo que queda por cobrar}. Si la comisión no se pudo cobrar y la copia estaba activa,
    la pausa con el motivo `comision_pendiente`."""
    ahora = ahora or _ahora()
    resumen = {"liquidada": False, "comision": 0.0, "pendiente": cobrar_pendientes(cliente, copia, estrategia)}
    hasta = _periodo_a_liquidar(cliente, copia, ahora)
    if hasta is None:
        return resumen
    final = copia["estado"] == "cerrada"
    try:
        fila = _liquidar(cliente, copia, hasta, final)
    except Exception as e:  # noqa: BLE001 - sin la liquidación atómica no se cobra nada: se reintenta en la próxima pasada
        print(f"[COMISIONES] copia {copia['id']}: no se pudo liquidar ({type(e).__name__}); se reintenta en la próxima pasada", flush=True)
        return resumen
    if fila is None or not fila["nueva"]:     # nada que liquidar, o ya lo liquidó otro trabajador (y el cobro lo hace quien la creó o `cobrar_pendientes`)
        if final and fila is not None:
            copia["comision_final_en"] = ahora.isoformat()
        resumen["pendiente"] = pendiente(cliente, copia["id"])
        return resumen
    copia["marca_agua"] = max(_n(copia.get("marca_agua")), fila["marca_agua_despues"])
    if final:
        copia["comision_final_en"] = ahora.isoformat()
    resumen.update({"liquidada": True, "comision": fila["comision"]})
    if fila["comision"] > 0 and not _pagar(cliente, copia, estrategia, fila):
        if copia["estado"] == "activa":
            cliente.table("copias").update({"estado": "pausada", "motivo_cierre": "comision_pendiente"}).eq("id", copia["id"]).execute()
            copia.update({"estado": "pausada", "motivo_cierre": "comision_pendiente"})
    resumen["pendiente"] = pendiente(cliente, copia["id"])
    return resumen



# -------------------------------------------------------------------------------------------------------
# ----------------------------------- FIN Piña y Jara comisiones .PY ------------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
