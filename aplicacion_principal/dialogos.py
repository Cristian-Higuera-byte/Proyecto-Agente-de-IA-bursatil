"""Diálogos que se dibujan en el script principal, fuera de los fragmentos en vivo."""


def renderizar_dialogos() -> None:
    # Diálogo del buscador (se abre con la bandera `mostrar_buscador`). Se renderiza
    # aquí, en el script principal, para que no choque con los fragmentos en vivo.
    from componentes_plataforma.buscador import render_buscador
    render_buscador()

    # Modal de confirmación de cierre de posición (Cartera). Igual que el buscador,
    # se renderiza fuera de los fragmentos en vivo.
    from componentes_plataforma.cartera_panel import render_modal_cerrar
    render_modal_cerrar()

    # Términos y condiciones de One-Click Trading (la primera vez que se activa).
    from componentes_plataforma.un_clic import render_modal_terminos
    render_modal_terminos()
