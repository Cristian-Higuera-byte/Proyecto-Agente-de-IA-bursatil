# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ----------------------------------------- INICIO Piña y Jara menu .PY ---------------------------------
# -------------------------------------------------------------------------------------------------------

"""
conectar_cuenta/menu.py
-----------------------
Piezas de la barra superior para las cuentas: la etiqueta DEMO / REAL siempre visible y las entradas del menú del
usuario para cambiar de cuenta o gestionarlas. Solo se dibujan con el modo multiusuario encendido.

Los enlaces del menú llevan el token de sesión (`s`) para que el cambio de cuenta no cierre la sesión; los procesa
`pantalla.requerir_cuenta`.
"""
import html
from urllib.parse import quote

import streamlit as st

from herramientas.backends import sesiones_capital

from .modo import cuentas_conectadas, modo_activo_demo

# Estilo común de cada entrada del menú del usuario (el mismo de usuario_menu.html)
_ESTILO_ENTRADA = ("display:flex; align-items:center; gap:10px; padding:9px 12px; border-radius:6px; "
                   "color:#e6edf3; font-size:13px; cursor:pointer; text-decoration:none;")


# TITULO ETIQUETA DE CUENTA

def etiqueta_cuenta() -> str:
    """Devuelve el HTML de la etiqueta de la cuenta activa (DEMO en azul, REAL en rojo), o '' con el modo apagado."""
    if not sesiones_capital.MULTIUSUARIO:
        return ""
    if modo_activo_demo():
        color, texto = "#58a6ff", "DEMO"
    else:
        color, texto = "#f85149", "REAL"
    return (f"<span title='Cuenta con la que estás operando' style='font-size:11px; font-weight:800; letter-spacing:.5px; "
            f"color:{color}; border:1px solid {color}; border-radius:5px; padding:2px 7px;'>{texto}</span>")


# TITULO ENTRADAS DEL MENU

def entradas_menu() -> str:
    """Devuelve el HTML de las entradas del menú del usuario: cambiar a la otra cuenta (si hay dos) y gestionar cuentas.

    Devuelve '' con el modo multiusuario apagado."""
    if not sesiones_capital.MULTIUSUARIO:
        return ""
    cuentas = cuentas_conectadas()
    token = quote(str(st.query_params.get("s", "")), safe="")
    en_demo = modo_activo_demo()
    entradas = []
    if cuentas.get("demo") and cuentas.get("real"):
        destino, rotulo = ("real", "Cambiar a cuenta Real") if en_demo else ("demo", "Cambiar a cuenta Demo")
        entradas.append(f"<a href='?cuenta={destino}&s={token}' target='_self' class='navegacion-menu-elemento' "
                        f"style='{_ESTILO_ENTRADA}'>{html.escape(rotulo)}</a>")
    entradas.append(f"<a href='?cuentas=1&s={token}' target='_self' class='navegacion-menu-elemento' "
                    f"style='{_ESTILO_ENTRADA}'>Mis cuentas</a>")
    return "".join(entradas) + "<div style='height:1px; background:#30363d; margin:4px 6px;'></div>"


# -------------------------------------------------------------------------------------------------------
# ------------------------------------------ FIN Piña y Jara menu .PY -----------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
