"""Módulo de generación de tablas y reportes estructurados para el agente.

NOMBRE DEL ARCHIVO: herramientas/tablas_tools.py
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from typing import Any

from fuentes import mt5_fuentes as mt5_fuente
from herramientas import analisis_tools
from herramientas.base import herramienta

OUTPUT_DIR = os.path.join("static", "reportes")
os.makedirs(OUTPUT_DIR, exist_ok=True)


@herramienta(
    descripcion=(
        "Genera tablas de datos financieras y reportes formateados en Markdown, HTML o CSV descargables. "
        "Permite estructurar reportes de 'posiciones_abiertas', 'riesgo_cartera', 'matriz_escenarios' "
        "o datos personalizados para exportación al usuario o dashboard."
    ),
    parametros={
        "tipo_reporte": {
            "type": "string",
            "enum": ["posiciones_abiertas", "riesgo_cartera", "datos_personalizados"],
            "description": "Tipo de contenido a tabular. Por defecto 'posiciones_abiertas'.",
        },
        "formato": {
            "type": "string",
            "enum": ["markdown", "html", "csv"],
            "description": "Formato de salida de la tabla. Por defecto 'markdown'.",
        },
        "datos_json": {
            "type": "string",
            "description": "Cadena JSON opcional con datos estructurados si tipo_reporte='datos_personalizados'.",
        },
    },
    nombre="generar_tabla_reporte",
)
def generar_tabla_reporte(
    tipo_reporte: str = "posiciones_abiertas",
    formato: str = "markdown",
    datos_json: str | None = None,
) -> dict[str, Any]:
    columnas: list[str] = []
    filas: list[list[Any]] = []

    # 1. Recopilar datos según el tipo de reporte
    if tipo_reporte == "posiciones_abiertas":
        pos_data = mt5_fuente.posiciones()
        posiciones = pos_data.get("posiciones", [])
        columnas = ["Ticket", "Símbolo", "Tipo", "Lotes", "Precio Apertura", "Precio Actual", "SL", "TP", "PnL ($)"]
        for p in posiciones:
            filas.append([
                p["ticket"],
                p["simbolo"],
                p["tipo"],
                p["lotes"],
                p["precio_apertura"],
                p["precio_actual"],
                p["sl"] or "Sin SL",
                p["tp"] or "Sin TP",
                p["beneficio"],
            ])

    elif tipo_reporte == "riesgo_cartera":
        riesgo_data = analisis_tools.analizar_riesgo_posicion()
        posiciones = riesgo_data.get("posiciones", [])
        columnas = ["Ticket", "Símbolo", "Tipo", "Lotes", "Distancia SL (Pips)", "Riesgo ($)", "Riesgo Equidad (%)", "Ratio R:R"]
        for r in posiciones:
            filas.append([
                r["ticket"],
                r["simbolo"],
                r["tipo"],
                r["lotes"],
                r.get("distancia_sl_pips") or "N/A",
                r.get("riesgo_estimado_usd") or "N/A",
                f"{r.get('riesgo_equidad_pct')}%" if r.get('riesgo_equidad_pct') else "N/A",
                r.get("ratio_riesgo_beneficio") or "N/A",
            ])

    elif tipo_reporte == "datos_personalizados" and datos_json:
        try:
            parsed = json.loads(datos_json)
            if isinstance(parsed, list) and len(parsed) > 0:
                columnas = list(parsed[0].keys())
                for item in parsed:
                    filas.append(list(item.values()))
        except Exception as e:
            return {"error": f"Error al parsear datos_json: {e}"}

    if not columnas:
        return {"error": "No hay datos para construir la tabla especificada."}

    # 2. Renderizar según formato
    resultado_texto = ""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"reporte_{tipo_reporte}_{timestamp}.{formato}"
    filepath = os.path.join(OUTPUT_DIR, filename)

    if formato == "markdown":
        header = "| " + " | ".join(columnas) + " |"
        sep = "| " + " | ".join(["---"] * len(columnas)) + " |"
        body = "\n".join(["| " + " | ".join(map(str, f)) + " |" for f in filas])
        resultado_texto = f"{header}\n{sep}\n{body}"

    elif formato == "html":
        th_str = "".join([f"<th>{c}</th>" for c in columnas])
        tr_str = "".join(["<tr>" + "".join([f"<td>{cell}</td>" for cell in f]) + "</tr>" for f in filas])
        resultado_texto = f"<table border='1' class='tabla-bursatil'><thead><tr>{th_str}</tr></thead><tbody>{tr_str}</tbody></table>"

    elif formato == "csv":
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(columnas)
            writer.writerows(filas)
        resultado_texto = f"Archivo CSV generado en {filepath}"

    # Si es Markdown o HTML, también guardamos copia en archivo para descarga
    if formato != "csv":
        with open(filepath, mode="w", encoding="utf-8") as f:
            f.write(resultado_texto)

    web_path = f"/static/reportes/{filename}"

    return {
        "fuente": "Generador de Tablas y Reportes",
        "tipo_reporte": tipo_reporte,
        "formato": formato,
        "total_filas": len(filas),
        "tabla_renderizada": resultado_texto,
        "archivo_guardado": filepath,
        "url_descarga": web_path,
    }