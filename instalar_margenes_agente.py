# -*- coding: utf-8 -*-
"""Instalador: márgenes de la nota y de la cuota de uso del agente en las tres copias del chat.

Uso (desde la carpeta raíz del proyecto):   python instalar_margenes_agente.py

La nota «Las respuestas del agente son informativas…» y la tarjeta «Uso del agente» llegaban pegadas a los bordes del panel (en el chat acoplado a la barra lateral la primera letra quedaba
cortada). Ahora tienen aire lateral igual que los controles y la zona de mensajes: 16 px en el chat flotante y el acoplado, y 18 px en el chat de la fila de abajo. Solo cambia
chat_flotante/estilos.css (la nota no se edita: se ajusta con CSS). Requiere haber instalado antes el chat flotante (el anclaje es el bloque «BOTONES DE REFRESCO OCULTOS»).
Es idempotente; si el archivo fue modificado a mano y no se reconoce, aborta SIN escribir nada."""
import os
import sys

# Cambios: archivo -> [(texto anterior, texto nuevo)]
CAMBIOS = {
 "componentes_plataforma/chat_flotante/estilos.css": [
  [
   "    /* TITULO BOTONES DE REFRESCO OCULTOS */",
   "    /* TITULO MARGENES DE LA NOTA Y DE LA CUOTA DEL AGENTE */\n    /* La nota «Las respuestas del agente son informativas…» (legal/paginas.py) y la tarjeta «Uso del agente» llegaban pegadas a los bordes del panel (y en el chat acoplado la primera letra\n       quedaba cortada). Ahora tienen el mismo aire lateral que los controles y la zona de mensajes de cada copia del chat. */\n    [class*=\"st-key-agente_chat_panel\"] [data-testid=\"stMarkdownContainer\"] > div[style*=\"font-size: 12px\"][style*=\"line-height: 1.4\"] { padding: 0 16px !important; margin: 4px 0 10px !important; box-sizing: border-box; }\n    .st-key-agente_chat_panel [data-testid=\"stMarkdownContainer\"] > div[style*=\"font-size: 12px\"][style*=\"line-height: 1.4\"] { padding: 0 18px !important; }\n    .st-key-agente_chat_panel .cuota-ia { margin: 0 18px 12px; }\n    .st-key-agente_chat_panel_flot .cuota-ia { margin: 0 16px 8px; }\n\n    /* TITULO BOTONES DE REFRESCO OCULTOS */"
  ]
 ]
}


# TITULO LEER
def _leer(ruta):
    with open(ruta, "rb") as f:
        return f.read().decode("utf-8")


# TITULO PLANIFICAR
def _planificar():
    """Calcula el texto final de cada archivo; devuelve (resultado, errores)."""
    salida, errores = {}, []
    for ruta, pares in CAMBIOS.items():
        if not os.path.isfile(ruta):
            errores.append(f"No existe {ruta} (ejecuta el instalador en la carpeta raíz del proyecto).")
            continue
        crudo = _leer(ruta)
        crlf = "\r\n" in crudo
        texto = crudo.replace("\r\n", "\n")
        for viejo, nuevo, *marca in pares:
            if (marca[0] if marca else nuevo) in texto:
                continue
            if texto.count(viejo) != 1:
                errores.append(f"{ruta}: no se reconoce el fragmento «{viejo[:60].strip()}…» (¿archivo modificado a mano?).")
                break
            texto = texto.replace(viejo, nuevo)
        else:
            salida[ruta] = (texto.replace("\n", "\r\n") if crlf else texto, crudo)
    return salida, errores


# TITULO PRINCIPAL
def main():
    salida, errores = _planificar()
    if errores:
        print("ABORTADO, no se modificó nada:")
        for e in errores:
            print("  -", e)
        return 1
    cambiados = 0
    for ruta, (texto, crudo) in salida.items():
        if texto != crudo:
            with open(ruta, "wb") as f:
                f.write(texto.encode("utf-8"))
            cambiados += 1
            print("  modificado:", ruta)
    print(f"Listo: {cambiados} archivo(s) modificado(s), {len(salida) - cambiados} ya estaban al día.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
