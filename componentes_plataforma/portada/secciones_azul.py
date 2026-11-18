# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ------------------------------------ INICIO Piña y Jara secciones_azul .PY ----------------------------
# -------------------------------------------------------------------------------------------------------

"""Bloques nuevos de la portada con el diseño azul propuesto por el cliente: cinta de precios, categorías de mercados, banner de inicio y franja de confianza.

Se suman a los de `secciones.py` (que no se toca): la cinta de precios usa las mismas cotizaciones de `datos.activos()` (en vivo o de ejemplo), y los textos de los banners están aquí mismo,
con los enlaces a `?acceso=crear` y a las secciones de la página. Los estilos están en `estilos_azul.css`."""
from __future__ import annotations

import time
from html import escape

from componentes_plataforma.portada import datos
from componentes_plataforma.portada.secciones import CREAR, _ico, _num

# Categorías de mercados que ofrece la plataforma: (ícono, nombre).
CATEGORIAS = (("show_chart", "Acciones<br>globales"), ("currency_exchange", "Forex<br>Divisas"), ("currency_bitcoin", "Criptomonedas"),
              ("diamond", "Materias<br>primas"), ("bar_chart_4_bars", "Índices<br>bursátiles"), ("pie_chart", "ETFs"))
# Cantidad máxima de instrumentos en la cinta de precios.
MAXIMO_CINTA = 5


# TITULO CINTA

def cinta() -> str:
    """Cinta horizontal con las cotizaciones más recientes (símbolo, precio y variación con su flecha) debajo del héroe. Usa `datos.activos()`: precios en vivo si hay lectura reciente y de ejemplo si no."""
    lista = datos.activos()[:MAXIMO_CINTA]
    if not lista:
        return ""
    celdas = ""
    for x in lista:
        sube = x["var"] >= 0
        celdas += (f"<div class='pj-p-cinta-item'><span class='pj-p-cinta-flecha {'pj-p-sube' if sube else 'pj-p-baja'}'>{'▲' if sube else '▼'}</span>"
                   f"<b>{escape(x['simbolo'])}</b><span class='pj-p-cinta-precio'>{_num(x['precio'], x['decimales'])}</span>"
                   f"<span class='pj-p-cinta-var {'pj-p-sube' if sube else 'pj-p-baja'}'>{'+' if sube else ''}{_num(x['var'], 2)}%</span></div>")
    ejemplo = any(x.get("ejemplo") for x in lista)
    hora = time.strftime("%H:%M", time.localtime(max(x["ts"] for x in lista))) if not ejemplo else ""
    pie = "Cotizaciones de ejemplo" if ejemplo else f"En vivo · {hora}"
    return (f"<section class='pj-p-cinta'><div class='pj-p-cont'><div class='pj-p-cinta-fila'>{celdas}</div>"
            f"<div class='pj-p-cinta-pie'><span class='pj-p-punto-vivo'></span>{pie}</div></div></section>")


# TITULO CATEGORIAS

def categorias() -> str:
    """Fila de las seis categorías de mercados (acciones, forex, criptomonedas, materias primas, índices y ETFs), cada una con su ícono; llevan a crear la cuenta."""
    items = "".join(f"<a class='pj-p-categoria' href='{CREAR}' target='_self'>{_ico(icono, 'pj-p-categoria-ico')}<span>{nombre}</span></a>" for icono, nombre in CATEGORIAS)
    return f"<section class='pj-p-categorias' id='mercados-cat'><div class='pj-p-cont'><div class='pj-p-categorias-fila'>{items}</div></div></section>"


# TITULO BANNER

def banner() -> str:
    """Banner destacado de inicio: invita a empezar con la cuenta demo (sin arriesgar capital) y lleva a los planes; a la derecha, un cohete con barras que suben."""
    barras = "".join(f"<i style='height:{h}%'></i>" for h in (22, 34, 30, 48, 42, 62, 56, 80))
    return ("<section class='pj-p-banner-sec'><div class='pj-p-cont'><div class='pj-p-banner'>"
            "<div class='pj-p-banner-texto'><span class='pj-p-banner-etq'>PARA EMPEZAR</span>"
            "<h2>Tu primer paso en el trading, sin arriesgar capital</h2>"
            "<p>Crea tu cuenta, conecta tu cuenta demo de Capital.com y prueba la plataforma y el agente de IA con dinero ficticio. Cuando quieras, pasas a un plan con más preguntas al agente.</p>"
            "<a class='pj-p-btn pj-p-btn-azul' href='#planes' target='_self'>Ver planes <span class='pj-p-flecha-simple'>→</span></a></div>"
            f"<div class='pj-p-banner-arte' aria-hidden='true'><div class='pj-p-banner-barras'>{barras}</div>{_ico('rocket_launch', 'pj-p-banner-cohete')}</div>"
            "</div></div></section>")


# TITULO CONFIANZA

def confianza() -> str:
    """Franja de confianza con tres garantías reales de la plataforma (el dinero queda en el bróker, credenciales cifradas y órdenes confirmadas por el usuario) y la tarjeta «Empieza hoy»."""
    items = (("account_balance", "Tu dinero queda en tu bróker", "La plataforma no custodia fondos"),
             ("lock", "Credenciales cifradas", "Tus claves de la API se guardan cifradas"),
             ("verified_user", "Tú confirmas cada orden", "El agente propone, tú decides"))
    celdas = "".join(f"<div class='pj-p-confianza-item'>{_ico(i, 'pj-p-confianza-ico')}<div><b>{escape(t)}</b><span>{escape(d)}</span></div></div>" for i, t, d in items)
    return (f"<section class='pj-p-confianza'><div class='pj-p-cont pj-p-confianza-fila'><div class='pj-p-confianza-lista'>{celdas}</div>"
            "<div class='pj-p-hoy'><div><b>Empieza hoy</b><span>Descubre todo lo que nuestra plataforma tiene para ofrecerte.</span>"
            f"<a class='pj-p-btn pj-p-btn-azul pj-p-btn-chico' href='{CREAR}' target='_self'>Crear cuenta <span class='pj-p-flecha-simple'>→</span></a></div>"
            f"{_ico('trending_up', 'pj-p-hoy-ico')}</div></div></section>")


# -------------------------------------------------------------------------------------------------------
# -------------------------------------- FIN Piña y Jara secciones_azul .PY -----------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
