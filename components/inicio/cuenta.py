"""Bloque de cuenta de Inicio: encabezado (saludo, chip de cuenta, Operar), tarjeta principal (equity, P/G,
saldo y márgenes) y "Salud de la cuenta". Los números llevan data-pj-* y los pinta el feed en vivo."""
import streamlit as st

from components.inicio.formato import estado_margen, fmt, mi
from tools.mt5_bridge import obtener_info_cuenta


def dibujar_cuenta(nombre: str):
    info = obtener_info_cuenta()
    if "error" in info:
        st.warning("No se pudo conectar con MetaTrader 5. Abre el terminal para ver tu cuenta.")
        return
    moneda = info.get("currency", "USD")
    login = info.get("login", "—")
    tipo = info.get("tipo", "Demo")
    equity = info.get("equity", 0.0)
    balance = info.get("balance", 0.0)
    profit = info.get("profit", 0.0)
    margin = info.get("margin", 0.0)
    libre = info.get("margin_free", 0.0)
    ml = info.get("margin_level", 0.0)
    lev = info.get("leverage", 0)
    uso = (margin / equity * 100) if equity else 0.0
    oculto = st.session_state.get("ini_ocultar", False)

    # Encabezado: saludo + chip de cuenta + Operar
    h1, h2, h3 = st.columns([3, 1.6, 0.8], vertical_alignment="bottom")
    with h1:
        st.html(f"<p class='ini-hola'>Hola{', ' + nombre.split()[0] if nombre else ''}</p>"
                "<div class='ini-title'>Resumen de tu cuenta</div>")
    with h2:
        if st.button(f"{tipo} · #{login}", key="ini_sel", icon=":material/account_balance_wallet:",
                     width="stretch"):
            st.session_state.ini_modal_cuentas = True
            st.rerun()
    with h3:
        if st.button("Operar", key="ini_operar", icon=":material/trending_up:", width="stretch"):
            st.session_state.nav_activo = "trading"
            st.rerun()

    def vivo(campo, texto, fmt_="usd", extra=""):
        if oculto:
            return "••••"
        return f"<span data-pj-acc='{campo}' data-pj-fmt='{fmt_}' {extra}>{texto}</span>"

    c_hero, c_sal = st.columns([1.75, 1], gap="medium")
    with c_hero:
        with st.container(key="ini_hero"):
            if st.button("", key="ini_ojo", help="Mostrar montos" if oculto else "Ocultar montos",
                         icon=":material/visibility:" if oculto else ":material/visibility_off:"):
                st.session_state.ini_ocultar = not oculto
                st.rerun(scope="fragment")
            up = profit >= 0
            # La moneda va FUERA del número en vivo (con el sufijo en un atributo
            # el espacio se perdía y se veía "-4,492.00USD").
            pl_html = ("••••" if oculto else
                       f"<span data-pj-acc='profit' data-pj-fmt='signed'>{profit:+,.2f}</span>"
                       f"<span style='margin-left:4px;'>{moneda}</span>")
            st.html(
                "<div class='hero-top'><span class='hero-lbl'>Equity</span>"
                f"<span class='hero-badge'>{tipo}</span></div>"
                f"<div class='hero-eq'>{vivo('equity', fmt(equity))}<small>{moneda}</small></div>"
                f"<div class='hero-pl {'up' if up else 'dn'}'>"
                f"{mi('trending_up' if up else 'trending_down', size=18)}{pl_html}"
                "<span class='t'>P/G flotante</span></div>"
                "<div class='kpis'>"
                f"<div class='kpi'><div class='k'>Saldo</div><div class='v'>{vivo('balance', fmt(balance))}</div></div>"
                f"<div class='kpi'><div class='k'>Margen libre</div><div class='v'>{vivo('margin_free', fmt(libre))}</div></div>"
                f"<div class='kpi'><div class='k'>Margen usado</div><div class='v'>{vivo('margin', fmt(margin))}</div></div>"
                "</div>"
            )
    with c_sal:
        with st.container(key="ini_salud"):
            estado, col = estado_margen(ml)
            st.html(
                "<div class='sal-title'>Salud de la cuenta</div>"
                "<div class='sal-nivel'><span class='k'>Nivel de margen</span>"
                f"<span class='sal-estado' style='color:{col};background:{col}1f;'>{estado}</span></div>"
                f"<div class='sal-nivel' style='margin-top:0'><span class='v' style='color:{col};'>"
                f"<span data-pj-acc='margin_level' data-pj-fmt='pct'>{(f'{ml:,.2f}%' if ml else '—')}</span>"
                "</span></div>"
                "<div class='sal-bar-lbl'><span>Margen usado del equity</span>"
                f"<b><span data-pj-acc='uso_margen' data-pj-fmt='pct'>{uso:,.2f}%</span></b></div>"
                f"<div class='sal-bar'><div data-pj-bar='uso_margen' style='width:{min(uso, 100):.1f}%;'></div></div>"
                "<div class='sal-rows'>"
                f"<div class='sal-row'><span class='k'>Apalancamiento</span><span class='v'>{f'{lev}:1' if lev else '—'}</span></div>"
                f"<div class='sal-row'><span class='k'>Crédito</span><span class='v'>"
                f"<span data-pj-acc='credit' data-pj-fmt='usd'>{fmt(info.get('credit', 0.0))}</span></span></div>"
                f"<div class='sal-row'><span class='k'>Servidor</span><span class='v'>{info.get('servidor', '—')}</span></div>"
                "</div>"
            )
