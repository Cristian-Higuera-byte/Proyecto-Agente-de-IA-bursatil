"""Prueba TEMPORAL de V15 contra el PostgreSQL real del servidor (se borra después de usarla).

Crea usuarios de prueba (v15-*@example.invalid) con una estrategia, copias, operaciones y billeteras propias, ejercita con hilos de verdad las funciones SQL `comision_liquidar` y
`billetera_recargar` y las compras de plan, y AL TERMINAR borra todo lo que creó (los usuarios, y en cascada sus datos). No toca ningún dato existente.
Uso (desde la carpeta del proyecto, en el servidor):  python probar_v15.py
"""
import os
import sys
import threading
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)
os.environ["BASE_DATOS"] = "postgres"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import configuracion                                                            # noqa: E402
from herramientas import base_datos_postgres, billetera, comisiones, gestor_autenticacion  # noqa: E402

FALLOS = []
CORREOS = ["v15-seguidor@example.invalid", "v15-gestor@example.invalid", "v15-recarga1@example.invalid", "v15-recarga2@example.invalid", "v15-compra@example.invalid"]


def comprobar(condicion, texto):
    """Anota y muestra el resultado de una comprobación."""
    print(("  OK   " if condicion else "  FALLA ") + texto, flush=True)
    if not condicion:
        FALLOS.append(texto)


c = base_datos_postgres.crear_cliente_desde_entorno()
c._maximo_conexiones = 14                # el pool normal es de 5: la prueba lanza más hilos a la vez
gestor_autenticacion._supabase = c
configuracion.PLANES_LIBRES = True


def limpiar():
    """Borra los usuarios de prueba (y, en cascada, sus billeteras, copias, operaciones, liquidaciones y compras)."""
    for correo in CORREOS:
        c.table("usuarios").delete().eq("email", correo).execute()


def hilos(n, funcion):
    """Lanza `n` hilos que arrancan a la vez y devuelve la lista de lo que cada uno devolvió."""
    salida, barrera = [], threading.Barrier(n)

    def uno(i):
        barrera.wait()
        try:
            salida.append(funcion(i))
        except Exception as e:  # noqa: BLE001
            salida.append(e)

    ts = [threading.Thread(target=uno, args=(i,)) for i in range(n)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return salida


def saldo_de(usuario):
    """Saldo de la billetera de un usuario."""
    filas = c.table("billetera_cuentas").select("saldo").eq("usuario_id", usuario).execute().data
    return float(filas[0]["saldo"]) if filas else 0.0


def pagos_de(usuario):
    """Pagos de comisión hechos por un usuario."""
    return c.table("billetera_movimientos").select("id,clave_unica").eq("usuario_id", usuario).eq("tipo", "comision_pagada").execute().data


try:
    limpiar()
    print("0) Requisitos")
    funciones = {f["proname"] for f in c.ejecutar_sentencia("SELECT proname FROM pg_proc WHERE proname IN (%s, %s)", ["comision_liquidar", "billetera_recargar"])}
    comprobar(funciones == {"comision_liquidar", "billetera_recargar"}, f"las funciones SQL existen: {sorted(funciones)}")
    tabla = c.ejecutar_sentencia("SELECT to_regclass(%s) AS t", ["billetera_compras"])[0]["t"]
    comprobar(tabla is not None, "la tabla billetera_compras existe")
    if FALLOS:
        raise SystemExit("faltan los objetos del SQL de V15; ejecutar liquidaciones_y_billetera_atomicas.sql")

    ids = {}
    for correo in CORREOS:
        ids[correo] = c.table("usuarios").insert({"nombre": "Prueba V15", "email": correo, "password_hash": "x"}).execute().data[0]["id"]
    seguidor, gestor = ids[CORREOS[0]], ids[CORREOS[1]]
    c.table("cuentas_inversor").insert({"usuario_id": seguidor}).execute()
    estrategia = c.table("estrategias").insert({"gestor_id": gestor, "nombre": "Estrategia V15", "comision_pct": 20}).execute().data[0]
    hace_40 = (datetime.now(timezone.utc) - timedelta(days=40)).replace(microsecond=0)
    c.rpc("billetera_mover", {"p_usuario": seguidor, "p_tipo": "ajuste", "p_monto": 500.0, "p_concepto": "saldo de prueba", "p_referencia": None, "p_clave": None}).execute()
    contador = {"n": 0}

    def crear_copia(estado="activa", cerrada_en=None):
        """Copia nueva del seguidor con ganancia de 80 (resultados 100 y -20)."""
        copia = c.table("copias").insert({"inversor_id": seguidor, "estrategia_id": estrategia["id"], "modo": "importe", "importe": 100, "estado": estado, "creada_en": hace_40.isoformat(),
                                          "cerrada_en": cerrada_en.isoformat() if cerrada_en else None}).execute().data[0]
        for resultado in (100.0, -20.0):
            contador["n"] += 1
            c.table("operaciones").insert({"usuario_id": seguidor, "id_broker": f"v15-{contador['n']}", "simbolo": "EURUSD", "lado": "compra", "volumen": 0.01, "precio_apertura": 1.1,
                                           "abierta_en": hace_40.isoformat(), "estado": "cerrada", "precio_cierre": 1.1, "cerrada_en": hace_40.isoformat(), "resultado": resultado,
                                           "origen": "copia", "copia_id": copia["id"]}).execute()
        return copia

    def copia_actual(copia_id):
        """La copia tal como está ahora en la base."""
        return c.table("copias").select("*").eq("id", copia_id).execute().data[0]

    print("1) Liquidación mensual: varios trabajadores con horas distintas (flujo completo de comisiones.revisar)")
    copia = crear_copia()
    estr = c.table("estrategias").select("*").eq("id", estrategia["id"]).execute().data[0]
    saldo_antes = saldo_de(seguidor)
    horas = [datetime.now(timezone.utc) + timedelta(seconds=s) for s in (0, 2, 5, 7, 11, 13)]
    hilos(6, lambda i: comisiones.revisar(c, copia_actual(copia["id"]), estr, ahora=horas[i]))
    filas = c.table("comisiones_rendimiento").select("*").eq("copia_id", copia["id"]).execute().data
    comprobar(len(filas) == 1, f"UNA sola liquidación con 6 trabajadores a la vez (filas: {len(filas)})")
    comprobar(filas and datetime.fromisoformat(str(filas[0]["periodo_hasta"])) == hace_40 + timedelta(days=30), "con el fin de período canónico (alta + 30 días)")
    comprobar(filas and float(filas[0]["comision"]) == 16.0 and filas[0]["clave_pago"], f"comisión de 16 con clave de pago: {filas[0]['clave_pago'] if filas else None}")
    comprobar(float(copia_actual(copia["id"])["marca_agua"]) == 80.0, "la marca de agua quedó en 80")
    comprobar(len(pagos_de(seguidor)) == 1 and saldo_antes - saldo_de(seguidor) == 16.0 and saldo_de(gestor) == 16.0, f"UN solo cobro: el seguidor pagó 16 y el gestor cobró {saldo_de(gestor)}")
    comprobar(filas and filas[0]["movimiento_billetera_id"] is not None, "la liquidación quedó enlazada al movimiento de la billetera")
    comisiones.revisar(c, copia_actual(copia["id"]), estr, ahora=hace_40 + timedelta(days=62))
    filas = c.table("comisiones_rendimiento").select("comision").eq("copia_id", copia["id"]).execute().data
    comprobar(len(filas) == 2 and sorted(float(f["comision"]) for f in filas) == [0.0, 16.0] and len(pagos_de(seguidor)) == 1, "el período siguiente liquida 0 (la marca ya avanzó): no se cobra dos veces la misma ganancia")

    print("2) Liquidación final: varios trabajadores")
    cierre = (datetime.now(timezone.utc) - timedelta(hours=2)).replace(microsecond=0)
    copia2 = crear_copia(estado="cerrada", cerrada_en=cierre)
    pagos_antes = len(pagos_de(seguidor))
    ahora = datetime.now(timezone.utc)
    hilos(6, lambda i: comisiones.revisar(c, copia_actual(copia2["id"]), estr, ahora=ahora + timedelta(seconds=i)))
    filas = c.table("comisiones_rendimiento").select("*").eq("copia_id", copia2["id"]).execute().data
    comprobar(len(filas) == 1 and datetime.fromisoformat(str(filas[0]["periodo_hasta"])) == cierre, "una sola liquidación final, con la hora de cierre como fin")
    comprobar(len(pagos_de(seguidor)) == pagos_antes + 1, "un solo cobro de la comisión final")
    comprobar(copia_actual(copia2["id"])["comision_final_en"] is not None, "la copia queda con la comisión final liquidada")

    print("3) Mensual y final a la vez sobre la misma ganancia")
    cierre3 = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(microsecond=0)
    copia3 = crear_copia(estado="cerrada", cerrada_en=cierre3)
    pagos_antes = len(pagos_de(seguidor))

    def mensual_o_final(i):
        """Trabajadores pares ven la copia activa (mensual) y los impares cerrada (final)."""
        d = copia_actual(copia3["id"])
        d["estado"] = "activa" if i % 2 == 0 else "cerrada"
        return comisiones.revisar(c, d, estr, ahora=datetime.now(timezone.utc) + timedelta(days=1))

    hilos(6, mensual_o_final)
    filas = c.table("comisiones_rendimiento").select("comision").eq("copia_id", copia3["id"]).execute().data
    comprobar(round(sum(float(f["comision"]) for f in filas), 2) == 16.0 and len(pagos_de(seguidor)) == pagos_antes + 1, f"comisiones {sorted(float(f['comision']) for f in filas)}: se cobra 16 UNA sola vez")

    print("4) Recargas simultáneas (billetera_recargar)")
    r1 = ids[CORREOS[2]]
    billetera._dueno = lambda: ("supabase", r1)
    res = hilos(10, lambda i: billetera.recargar_virtual(1000))
    bien = [x for x in res if isinstance(x, float)]
    comprobar(len(bien) == 5 and saldo_de(r1) == 5000.0, f"10 recargas de 1000 a la vez con tope mensual de 5000: salen {len(bien)}, saldo {saldo_de(r1)}")
    comprobar(all("tope de recargas" in str(x) for x in res if not isinstance(x, float)), "las demás se rechazan con el mensaje del tope mensual")
    r2 = ids[CORREOS[3]]
    billetera._dueno = lambda: ("supabase", r2)
    maximo, tope = configuracion.BILLETERA["saldo_maximo"], configuracion.BILLETERA["recarga_mensual_max"]
    configuracion.BILLETERA["saldo_maximo"], configuracion.BILLETERA["recarga_mensual_max"] = 3000.0, 100000.0
    res = hilos(8, lambda i: billetera.recargar_virtual(1000))
    configuracion.BILLETERA["saldo_maximo"], configuracion.BILLETERA["recarga_mensual_max"] = maximo, tope
    bien = [x for x in res if isinstance(x, float)]
    comprobar(len(bien) == 3 and saldo_de(r2) == 3000.0, f"8 recargas de 1000 a la vez con saldo máximo de 3000: salen {len(bien)}, saldo {saldo_de(r2)}")
    comprobar(sum(1 for m in c.table("billetera_movimientos").select("id").eq("usuario_id", r2).eq("tipo", "recarga_virtual").execute().data) == 3, "el libro tiene exactamente 3 movimientos de recarga")

    print("5) Compras de plan con estado")
    comprador = ids[CORREOS[4]]
    billetera._dueno = lambda: ("supabase", comprador)
    c.rpc("billetera_mover", {"p_usuario": comprador, "p_tipo": "ajuste", "p_monto": 200.0, "p_concepto": "saldo de prueba", "p_referencia": None, "p_clave": None}).execute()
    plan = next(p for p in configuracion.PLANES_IA if p != "gratis")
    estado_activar = {"falla": None, "ok": True}

    def activar(plan_, origen="prueba"):
        """Activa el plan, o se interrumpe el proceso, según el escenario."""
        if estado_activar["falla"]:
            raise estado_activar["falla"]
        return estado_activar["ok"]

    billetera.cuota_ia.fijar_plan = activar

    def compras():
        """Estados de las compras del comprador."""
        return [x["estado"] for x in c.table("billetera_compras").select("estado").eq("usuario_id", comprador).order("id").execute().data]

    def cobros():
        """Cobros de compras del comprador."""
        return c.table("billetera_movimientos").select("id").eq("usuario_id", comprador).eq("tipo", "compra_plan").execute().data

    res = hilos(4, lambda i: billetera.comprar_plan(plan, 30.0))
    comprobar(len(cobros()) == 1 and saldo_de(comprador) == 170.0 and compras() == ["activada"], f"4 clics a la vez cobran UNA vez: cobros {len(cobros())}, saldo {saldo_de(comprador)}, compras {compras()}")
    c.table("billetera_compras").delete().eq("usuario_id", comprador).execute()
    estado_activar["falla"] = RuntimeError("el proceso se interrumpió")
    try:
        billetera.comprar_plan(plan, 30.0)
    except RuntimeError:
        pass
    comprobar(compras() == ["cobrada"], f"interrupción entre cobrar y activar: la compra queda «cobrada» ({compras()})")
    estado_activar["falla"] = None
    comprobar(billetera.reanudar_compras(gracia_min=0) == 1 and compras() == ["activada"] and len(cobros()) == 2, "al reanudar se activa el plan sin cobrar de nuevo (2 cobros en total: el de antes y este)")
    try:
        c.table("billetera_compras").insert({"usuario_id": comprador, "plan": "unico", "precio": 10, "estado": "iniciada"}).execute()
        c.table("billetera_compras").insert({"usuario_id": comprador, "plan": "unico", "precio": 10, "estado": "cobrada"}).execute()
        comprobar(False, "el índice rechaza dos compras en curso del mismo plan")
    except Exception as e:  # noqa: BLE001
        comprobar("billetera_compras_en_curso" in str(e), "el índice único rechaza dos compras en curso del mismo usuario y plan")
finally:
    limpiar()
    restos = c.table("usuarios").select("id").in_("email", CORREOS).execute().data
    comprobar(restos == [], "se borraron los usuarios de prueba y, en cascada, todos sus datos")

print()
if FALLOS:
    print(f"{len(FALLOS)} comprobaciones FALLARON:")
    for f in FALLOS:
        print(" -", f)
    sys.exit(1)
print("Todas las comprobaciones pasaron.")
