import streamlit as st

# (icono material, clave)
ITEMS = [
    (":material/home:", "home"),
    (":material/show_chart:", "mercados"),
    (":material/work:", "portafolio"),
    (":material/assignment:", "ordenes"),
    (":material/bar_chart:", "analisis"),
    (":material/rocket_launch:", "promociones"),
    (":material/settings:", "ajustes"),
]


def renderizar_barra_navegacion():
    st.markdown("""
    <style>
        /* Quita el padding lateral para que la barra quede pegada al borde */
        .block-container {
            padding-left: 0 !important;
            padding-top: 1rem !important;
        }

        /* Solo la columna que contiene el marcador .pj-nav */
        div[data-testid="stColumn"]:has(.pj-nav),
        div[data-testid="column"]:has(.pj-nav) {
            background: #0d1117;
            border-right: 1px solid #30363d;
            min-height: 100vh;
            padding: 12px 0 !important;
            align-items: center;
        }
        div[data-testid="stColumn"]:has(.pj-nav) > div,
        div[data-testid="column"]:has(.pj-nav) > div {
            align-items: center;
            gap: 6px;
        }

        /* Logo */
        .pj-logo {
            font-weight: 900;
            font-size: 26px;
            letter-spacing: -1px;
            text-align: center;
            background: linear-gradient(135deg, #ff4b4b 0%, #ff8f00 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 18px;
        }

        /* Botones: iconos sin caja */
        div[data-testid="stColumn"]:has(.pj-nav) button,
        div[data-testid="column"]:has(.pj-nav) button {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: #8b949e !important;
            width: 44px !important;
            height: 44px !important;
            min-height: 44px !important;
            padding: 0 !important;
            border-radius: 10px !important;
            margin: 0 auto;
        }
        div[data-testid="stColumn"]:has(.pj-nav) button p,
        div[data-testid="column"]:has(.pj-nav) button p {
            font-size: 24px !important;
            line-height: 1 !important;
        }
        div[data-testid="stColumn"]:has(.pj-nav) button:hover,
        div[data-testid="column"]:has(.pj-nav) button:hover {
            background: rgba(255,255,255,0.08) !important;
            color: #fff !important;
        }

        /* Botón activo (type="primary") -> verde como en XM */
        div[data-testid="stColumn"]:has(.pj-nav) button[kind="primary"],
        div[data-testid="column"]:has(.pj-nav) button[kind="primary"],
        div[data-testid="stColumn"]:has(.pj-nav) [data-testid="stBaseButton-primary"] {
            background: rgba(34,197,94,0.12) !important;
            color: #22c55e !important;
        }
    </style>
    <div class="pj-nav"></div>
    """, unsafe_allow_html=True)

    if "nav_activo" not in st.session_state:
        st.session_state.nav_activo = "mercados"

    st.markdown('<div class="pj-logo">P&J</div>', unsafe_allow_html=True)

    for icono, clave in ITEMS:
        activo = st.session_state.nav_activo == clave
        if st.button(
            icono,
            key=f"nav_btn_{clave}",
            type="primary" if activo else "secondary",
            help=clave.capitalize(),
        ):
            st.session_state.nav_activo = clave
            st.rerun()

    # Espaciador: empuja el soporte hacia abajo (ajusta el 520px a tu gusto)
    st.markdown("<div style='height: calc(100vh - 560px);'></div>",
                unsafe_allow_html=True)

    if st.button(":material/headset_mic:", key="nav_soporte", help="Soporte y ayuda técnica"):
        st.toast("Soporte técnico de Piña & Jara activo.")