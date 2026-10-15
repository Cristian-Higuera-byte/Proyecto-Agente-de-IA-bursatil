"""
acceso/sesion.py
---------------
Mecánica de la sesión de usuario (sin UI): iniciar, cerrar y restaurar la sesión a
partir del token que vive en la URL (?s=...). El token lo guarda almacen_sesiones en el
servidor, así la sesión sobrevive a un F5 mientras la consola esté encendida.
"""
import streamlit as st

from herramientas import almacen_sesiones


def cerrar_sesion() -> None:
    """Limpia la sesión del usuario (y el token en memoria del servidor)."""
    almacen_sesiones.eliminar(st.query_params.get("s", ""))
    for clave in ("usuario_autenticado", "usuario_info"):
        st.session_state.pop(clave, None)


def iniciar_sesion(usuario: dict) -> None:
    """Marca la sesión, guarda el token en la URL (para que sobreviva al F5) y hace
    rerun. El overlay de carga de aplicacion.py tapa el login mientras el dashboard se arma,
    así se entra directo sin verlo encima."""
    st.session_state.usuario_autenticado = True
    st.session_state.usuario_info = usuario
    st.query_params["s"] = almacen_sesiones.crear(usuario)  # persiste tras F5
    st.rerun()


def usuario_en_sesion() -> dict | None:
    """Usuario ya autenticado en esta pestaña, o restaurado desde el token de la URL
    tras un F5 (si el servidor aún lo tiene). None si no hay sesión."""
    if st.session_state.get("usuario_autenticado"):
        return st.session_state.get("usuario_info", {})

    # Tras un F5, session_state se vacía pero el token sigue en la URL:
    # si el servidor aún lo tiene (consola encendida), restauramos la sesión.
    token = st.query_params.get("s")
    if token:
        usuario = almacen_sesiones.obtener(token)
        if usuario:
            st.session_state.usuario_autenticado = True
            st.session_state.usuario_info = usuario
            return usuario
    return None
