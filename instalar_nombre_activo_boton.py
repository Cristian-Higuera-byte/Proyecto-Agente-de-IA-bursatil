# -*- coding: utf-8 -*-
"""Instalador: sin la pestaña lateral de la lista de activos; el nombre del activo se ve como botón.

Uso (desde la carpeta raíz del proyecto):   python instalar_nombre_activo_boton.py

  * riel/estilos.css: la pestaña lateral naranja (que tapaba las herramientas del gráfico en pantalla completa) deja de mostrarse y el contenido ya no reserva
    58 px a la izquierda.
  * grafico/cabecera_precio.py: en celular y tablet (hasta 992 px de ancho, en vertical y horizontal, también en pantalla completa) el nombre del activo de la
    cabecera se ve como botón (píldora con borde azul y flecha ▾) y al pulsarlo abre la lista de activos o los favoritos, como ya hacía.
Es idempotente; si un archivo fue modificado a mano y no se reconoce, aborta SIN escribir nada."""
import os
import sys

# Cambios: archivo -> [(texto anterior, texto nuevo)]
CAMBIOS = {
 "componentes_plataforma/riel/estilos.css": [
  [
   "        /* En Trading, la pestaña de la lista de activos queda pegada al borde izquierdo: el contenido se corre a la derecha lo que ella mide (46 px) más un aire, para que no\n           tape el gráfico. En Cartera, que no tiene lista ni pestaña, no se reserva nada. */\n        html:has(.st-key-pj_pestana_activos) .block-container { padding-left: 58px !important; }\n",
   "        /* La pestaña lateral de la lista de activos ya no se muestra (tapaba las herramientas del gráfico en pantalla completa): la lista se abre tocando el nombre del\n           activo en la cabecera de precio, y por eso el contenido ya no reserva sitio a la izquierda. */\n"
  ],
  [
   "        .pj-pestana-activos { display: flex; align-items: center;",
   "        .pj-pestana-activos { display: none !important; align-items: center;"
  ]
 ],
 "componentes_plataforma/grafico/cabecera_precio.py": [
  [
   "                .pj-cab-simbolo {{ cursor: pointer; }}\n                .pj-cab-simbolo::after {{ content: \" \\\\25BE\"; color: #8b949e; font-size: 14px; }}\n",
   "                /* El nombre del activo es el botón que abre la lista de activos (y los favoritos): se ve como un botón, con borde, fondo y flecha. */\n                .pj-cab-simbolo {{ cursor: pointer; display: inline-flex; align-items: center; gap: 4px; padding: 3px 9px 3px 11px; border-radius: 14px;\n                    background: #1f2937; border: 1px solid #58a6ff88; box-shadow: 0 0 0 1px #58a6ff22; -webkit-tap-highlight-color: transparent; }}\n                .pj-cab-simbolo::after {{ content: \"\\\\25BE\"; color: #58a6ff; font-size: 15px; line-height: 1; }}\n                .pj-cab-simbolo:active, html.pj-panel-activos .pj-cab-simbolo, html.pj-panel-favorito .pj-cab-simbolo {{ background: #12263f; border-color: #58a6ff; }}\n"
  ],
  [
   "<span class='pj-cab-simbolo' style='font-size: 20px; font-weight: bold; color: #ffffff;'>",
   "<span class='pj-cab-simbolo' role='button' title='Ver lista de activos' style='font-size: 20px; font-weight: bold; color: #ffffff;'>"
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
