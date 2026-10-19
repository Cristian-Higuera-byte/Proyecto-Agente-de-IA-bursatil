# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ----------------------------------- INICIO Piña y Jara tarjetas .PY -----------------------------------
# -------------------------------------------------------------------------------------------------------

"""Tarjeta HTML de una noticia (la usan el carrusel y "Más noticias")."""


# TITULO TARJETA HTML

def tarjeta_html(n: dict) -> str:
    """Devuelve el HTML de una tarjeta de noticia: imagen, título (2 líneas), descripción (2 líneas, 110
    caracteres) y fecha.

    Recibe el diccionario de la noticia (`img`, `title`, `desc`, `fecha`). Los estilos van en línea y el
    recorte a dos líneas usa `-webkit-line-clamp`. Quien la llama pone encima un botón invisible (ver
    `estilos.css`) para que toda la tarjeta sea clicable."""
    return f"""
      <div style="display:flex; flex-direction:column;">
        <img src="{n['img']}" referrerpolicy="no-referrer"
             style="width:100%; height:130px; object-fit:cover; border-radius:10px; background:#161b22;">
        <p style="color:#e6edf3; font-size:14px; font-weight:600; line-height:1.3;
                  margin:9px 0 4px; display:-webkit-box; -webkit-line-clamp:2;
                  -webkit-box-orient:vertical; overflow:hidden;">{n['title']}</p>
        <p style="color:#8b949e; font-size:12px; line-height:1.4; margin:0 0 6px;
                  display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical;
                  overflow:hidden;">{n['desc'][:110]}</p>
        <span style="color:#586174; font-size:11px;">{n['fecha']}</span>
      </div>
    """


# -------------------------------------------------------------------------------------------------------
# ------------------------------------- FIN Piña y Jara tarjetas .PY ------------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
