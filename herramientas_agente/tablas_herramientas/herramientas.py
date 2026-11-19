# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ---------------------------------- INICIO Piña y Jara herramientas .PY --------------------------------
# -------------------------------------------------------------------------------------------------------

"""Herramientas registradas para el agente de tablas y reportes (los esquemas viven en esquemas.json).

Registra ``generar_tabla_reporte``, que arma tablas de posiciones, riesgo o
datos personalizados y las entrega en Markdown, HTML o CSV, guardando además un archivo en la carpeta PRIVADA del usuario (V17 de la auditoría: sin carpeta común, sin nombres predecibles,
HTML con las celdas escapadas y CSV con las fórmulas neutralizadas).
"""
from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Any

from fuentes import mt5_fuentes as mt5_fuente
from herramientas import archivos_privados
from herramientas_agente import analisis_herramientas
from herramientas_agente.base import cargar_json, herramienta
from herramientas_agente.tablas_herramientas.auxiliares import EXTENSION_DE_FORMATO, LIMITES, TIPOS_DE_REPORTE

# Esquemas (descripción y parámetros) de la herramienta, leídos de esquemas.json.
_ESQ = cargar_json(Path(__file__).parent / "esquemas.json")
# Una celda de hoja de cálculo que EMPIEZA con alguno de estos caracteres se interpreta como fórmula (Excel, LibreOffice, Google Sheets): se antepone una comilla simple.
_INICIOS_DE_FORMULA = ("=", "+", "-", "@", "\t", "\r", "\n")


# TITULO RECORTAR

def _recortar(texto: str) -> str:
    """Texto de una celda con el largo máximo permitido (se agrega «…» si se cortó)."""
    maximo = LIMITES["celda"]
    return texto if len(texto) <= maximo else texto[:maximo - 1] + "…"


# TITULO CELDA HTML

def _celda_html(valor: Any) -> str:
    """Celda lista para ir DENTRO de un `<td>` o `<th>`: el texto se escapa (`<`, `>`, `&` y comillas), así una etiqueta o un script en los datos se muestra como texto y no se ejecuta."""
    return html.escape(_recortar("" if valor is None else str(valor)), quote=True)


# TITULO CELDA MARKDOWN

def _celda_markdown(valor: Any) -> str:
    """Celda de una tabla Markdown: sin saltos de línea y con la barra vertical escapada, para que un dato no rompa la tabla ni agregue columnas."""
    texto = _recortar("" if valor is None else str(valor))
    return texto.replace("\r", " ").replace("\n", " ").replace("|", "\\|")


# TITULO ES NUMERO

def _es_numero(texto: str) -> bool:
    """True si el texto es un número normal (por ejemplo «-12.5»): un negativo legítimo no es una fórmula."""
    try:
        float(texto)
        return True
    except ValueError:
        return False


# TITULO CELDA CSV

def _celda_csv(valor: Any) -> Any:
    """Celda para un CSV con las fórmulas neutralizadas.

    Los números reales (int, float, bool) pasan tal cual. Un texto que empieza (aunque sea después de espacios) con `=`, `+`, `-`, `@`, tabulador o salto de línea se interpretaría como fórmula
    al abrir el archivo en una hoja de cálculo (puede ejecutar comandos o filtrar datos): se le antepone una comilla simple, que la hoja muestra como texto. Un texto que es un número («-12.5») no se toca."""
    if valor is None:
        return ""
    if isinstance(valor, (bool, int, float)):
        return valor
    texto = _recortar(str(valor))
    if texto.lstrip(" ")[:1] in _INICIOS_DE_FORMULA and not _es_numero(texto.strip()):
        return "'" + texto
    return texto


# TITULO GENERAR TABLA REPORTE

@herramienta(**_ESQ["generar_tabla_reporte"])
def generar_tabla_reporte(
    tipo_reporte: str = "posiciones_abiertas",
    formato: str = "markdown",
    datos_json: str | None = None,
) -> dict[str, Any]:
    """Genera una tabla de reporte y la guarda como archivo privado del usuario, descargable desde el chat.

    Recibe el tipo de reporte (posiciones_abiertas, riesgo_cartera o
    datos_personalizados), el formato de salida (markdown, html o csv) y, para
    los datos personalizados, una lista JSON de objetos con las mismas claves. Los datos salen de
    MT5 (posiciones) o del análisis de riesgo. Escribe un archivo con nombre aleatorio en la carpeta privada del usuario (nunca en una carpeta pública ni común). Devuelve el
    texto de la tabla, el número de filas y la ruta del archivo, o ``{"error": ...}`` si el tipo o el formato no son válidos, no hay datos o el JSON es inválido.
    """
    # Solo se aceptan los tipos y formatos conocidos: lo que llegue fuera de la lista no se usa para nada (tampoco para armar el nombre del archivo).
    if tipo_reporte not in TIPOS_DE_REPORTE:
        return {"error": f"Tipo de reporte no válido. Usa uno de: {', '.join(TIPOS_DE_REPORTE)}."}
    if formato not in EXTENSION_DE_FORMATO:
        return {"error": f"Formato no válido. Usa uno de: {', '.join(EXTENSION_DE_FORMATO)}."}

    # Columnas y filas de la tabla, que se rellenan según el tipo de reporte, y cuántas filas traían los datos de origen (para avisar si se recortó).
    columnas: list[str] = []
    filas: list[list[Any]] = []
    total_origen = 0

    # 1. Recopilar datos según el tipo de reporte
    if tipo_reporte == "posiciones_abiertas":
        posicion_data = mt5_fuente.posiciones()
        posiciones = posicion_data.get("posiciones", [])
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

    # Reporte de riesgo por posición, tomado del análisis de riesgo.
    elif tipo_reporte == "riesgo_cartera":
        riesgo_data = analisis_herramientas.analizar_riesgo_posicion()
        posiciones = riesgo_data.get("posiciones", [])
        columnas = ["Ticket", "Símbolo", "Tipo", "Lotes", "Distancia al SL (Pips)", "Riesgo ($)", "Riesgo Equidad (%)", "Ratio R:R"]
        for r in posiciones:
            filas.append([
                r["ticket"],
                r["simbolo"],
                r["tipo"],
                r["lotes"],
                r.get("distancia_sl_desde_precio_actual_pips") or "N/A",
                r.get("riesgo_estimado_usd") or "N/A",
                f"{r.get('riesgo_equidad_pct')}%" if r.get('riesgo_equidad_pct') else "N/A",
                r.get("ratio_riesgo_beneficio") or "N/A",
            ])

    # Datos libres: el JSON debe ser una lista de objetos; las columnas salen del primero y cada fila se arma con ESAS columnas (una clave de más o de menos no descuadra la tabla).
    elif tipo_reporte == "datos_personalizados" and datos_json:
        if len(datos_json) > LIMITES["json"]:
            return {"error": "datos_json es demasiado grande."}
        try:
            parsed = json.loads(datos_json)
            if isinstance(parsed, list) and len(parsed) > 0:
                if not all(isinstance(elemento, dict) for elemento in parsed):
                    return {"error": "datos_json debe ser una lista de objetos."}
                claves = list(parsed[0].keys())[:LIMITES["columnas"]]
                columnas = [str(c) for c in claves]
                total_origen = len(parsed)
                for elemento in parsed[:LIMITES["filas"]]:
                    filas.append([elemento.get(c, "") for c in claves])
        except Exception as e:
            return {"error": f"Error al parsear datos_json: {e}"}

    # Sin columnas no hay nada que mostrar.
    if not columnas:
        return {"error": "No hay datos para construir la tabla especificada."}
    truncada = total_origen > len(filas)

    # 2. Renderizar según formato
    resultado_texto = ""
    # Archivo NUEVO en la carpeta privada del usuario, con nombre aleatorio (dos exportaciones a la vez no se pisan y el nombre no se puede adivinar).
    filepath = archivos_privados.nuevo_archivo("reportes", EXTENSION_DE_FORMATO[formato])

    # Tabla Markdown: encabezado, separador y filas.
    if formato == "markdown":
        cabecera = "| " + " | ".join(_celda_markdown(c) for c in columnas) + " |"
        separador = "| " + " | ".join(["---"] * len(columnas)) + " |"
        cuerpo = "\n".join(["| " + " | ".join(_celda_markdown(celda) for celda in f) + " |" for f in filas])
        resultado_texto = f"{cabecera}\n{separador}\n{cuerpo}"

    # Tabla HTML simple con la clase tabla-bursatil; encabezados y celdas van ESCAPADOS.
    elif formato == "html":
        th_str = "".join([f"<th>{_celda_html(c)}</th>" for c in columnas])
        tr_str = "".join(["<tr>" + "".join([f"<td>{_celda_html(celda)}</td>" for celda in f]) + "</tr>" for f in filas])
        resultado_texto = f"<table border='1' class='tabla-bursatil'><thead><tr>{th_str}</tr></thead><tbody>{tr_str}</tbody></table>"

    # CSV: se escribe directamente en el archivo, con las fórmulas neutralizadas.
    elif formato == "csv":
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([_celda_csv(c) for c in columnas])
            writer.writerows([[_celda_csv(celda) for celda in fila] for fila in filas])
        resultado_texto = "Archivo CSV generado (se descarga desde el chat)."

    # Si es Markdown o HTML, también guardamos copia en archivo para descarga
    if formato != "csv":
        with open(filepath, mode="w", encoding="utf-8") as f:
            f.write(resultado_texto)

    return {
        "fuente": "Generador de Tablas y Reportes",
        "tipo_reporte": tipo_reporte,
        "formato": formato,
        "total_filas": len(filas),
        "truncada": truncada,
        "tabla_renderizada": resultado_texto,
        "archivo_guardado": str(filepath),
        "id_archivo": filepath.stem,
        "mensaje": "El archivo quedó guardado de forma privada y el usuario lo descarga con el botón del chat. No incluyas rutas ni enlaces en tu respuesta.",
    }


# -------------------------------------------------------------------------------------------------------
# ----------------------------------- FIN Piña y Jara herramientas .PY ----------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
