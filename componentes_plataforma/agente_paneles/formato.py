"""Utilidades de formato de los paneles del agente (todo texto que viene del agente/MT5 se escapa)."""
import html
from datetime import datetime
from typing import Any


def esc(valor: Any) -> str:
    return html.escape("" if valor is None else str(valor), quote=True)


def num(valor: Any) -> str:
    if valor in (None, 0, ""):
        return "—"
    try:
        return f"{float(valor):.5f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return esc(valor)


def hora(iso: Any) -> str:
    try:
        dt = datetime.fromisoformat(str(iso))
    except (TypeError, ValueError):
        return esc(iso)
    return dt.strftime("%H:%M") if dt.date() == datetime.now().date() else dt.strftime("%d/%m %H:%M")


def titulo(o: dict[str, Any]) -> str:
    simbolo = esc(o.get("simbolo") or "—")
    if o.get("accion") == "cerrar":
        ticket = f"#{esc(o['ticket_objetivo'])}" if o.get("ticket_objetivo") else "posición"
        return f"CERRAR {ticket} · {simbolo}"
    lado = str(o.get("lado") or "").lower()
    clase = "buy" if lado == "compra" else "sell" if lado == "venta" else ""
    try:
        vol = f" {float(o['volumen']):g}" if o.get("volumen") else ""
    except (TypeError, ValueError):
        vol = ""
    return f"<span class='{clase}'>{esc(lado.upper() or '—')}</span>{vol} · {simbolo}"


def detalle(o: dict[str, Any]) -> str:
    if o.get("estado") in ("EJECUTADA", "RECHAZADA_RIESGO", "ERROR"):
        txt = o.get("detalle") or o.get("justificacion")
    else:
        txt = o.get("justificacion") or o.get("detalle")
    txt = (txt or "").strip()
    corto = txt if len(txt) <= 110 else txt[:107] + "…"
    return f"<div class='ag-det' title='{esc(txt)}'>{esc(corto)}</div>" if txt else ""


def clase_lado(o: dict[str, Any]) -> str:
    """'buy' | 'sell' | 'cerrar': define el color de la franja lateral de la fila."""
    if o.get("accion") == "cerrar":
        return "cerrar"
    lado = str(o.get("lado") or "").lower()
    return "buy" if lado == "compra" else "sell" if lado == "venta" else "cerrar"


def cabecera_agente(icono: str, titulo: str, subtitulo: str) -> str:
    """Cabecera de panel (icono Material + título + subtítulo), igual que 'Lista de activos'."""
    return (
        f"<div class='ag-head'><div class='ic'><span class='ag-mi'>{esc(icono)}</span></div>"
        f"<div><div class='ag-title'>{esc(titulo)}</div><div class='ag-sub'>{esc(subtitulo)}</div></div></div>"
    )


def vacio(icono: str, texto: str) -> str:
    return f"<div class='ag-empty'><span class='ag-mi'>{esc(icono)}</span>{esc(texto)}</div>"


def marca_auto(o: dict[str, Any]) -> str:
    """Etiqueta AUTO si la orden la ejecutó una vigilancia automática (sin confirmación manual)."""
    return "<span class='ag-auto'>AUTO</span>" if o.get("origen") == "automatica" else ""


def kv(etiqueta: str, valor: str, clase: str = "") -> str:
    return f"<div class='ag-kv'><span>{esc(etiqueta)}</span><b class='{clase}'>{valor}</b></div>"
