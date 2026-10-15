"""Modal de una noticia: imagen, título, botón para abrirla en Investing.com y vista previa incrustada."""
import streamlit as st


def _contenido_modal(n: dict):
    st.html(f"""
        <img src="{n['img']}" referrerpolicy="no-referrer"
             style="width:100%; height:260px; object-fit:cover; border-radius:10px; background:#161b22;">
        <h2 style="color:#ffffff; font-size:24px; font-weight:800; line-height:1.3; margin:14px 0 6px;">{n['title']}</h2>
        <p style="color:#586174; font-size:12px; margin:0 0 12px;">{n['fecha']}</p>
    """)
    # Investing muestra muro de pago/login dentro del iframe y BLOQUEA el inicio de
    # sesión embebido (los popups de OAuth y las cookies de terceros no funcionan en un
    # iframe de otro sitio: es una protección del navegador, no un fallo nuestro). Por eso
    # se ofrece abrir la noticia en una PESTAÑA REAL, donde sí se puede loguear y leer.
    st.link_button("Abrir en Investing.com ↗", n["link"], type="primary", width="stretch")
    # El artículo se incrusta igual, como vista previa. Las páginas de artículo de
    # Investing permiten framing (sin X-Frame-Options), pero el contenido va paywalleado.
    st.iframe(n["link"], height=620)


def abrir_modal(n: dict):
    def _al_cerrar():
        st.session_state.noticia_abierta = None

    @st.dialog("Noticia", width="large", on_dismiss=_al_cerrar)
    def _dlg():
        _contenido_modal(n)

    _dlg()
