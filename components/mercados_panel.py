"""
mercados_panel.py
-----------------
Página "Mercados" (botón de la barra lateral), estilo es.investing.com:
un selector de categoría (Índices, Divisas, Materias primas, Criptomonedas,
Acciones) y una tabla con Último, Máximo, Mínimo, Var., % Var. y Hora.

Los datos salen de MetaTrader 5 (tick + máximos/mínimos de la sesión), usando
el resolvedor de símbolos para que funcione con o sin sufijo "..." del bróker.
"""
from datetime import datetime

import streamlit as st
import MetaTrader5 as mt5  # type: ignore[import-untyped]

from tools.mt5_bridge import inicializar_mt5, resolver_simbolo
from components.favoritos_bar import icono_activo

# Catálogo curado por categoría: (símbolo base, nombre a mostrar).
# El resolvedor mapea al nombre real del bróker; si no existe, la fila se omite.
_CATALOGO = {
    "Índices": [
        ("US30", "Dow Jones"), ("US500", "S&P 500"), ("NAS100", "Nasdaq 100"),
        ("GER40", "DAX (Alemania)"), ("UK100", "FTSE 100"), ("FRA40", "CAC 40"),
        ("ESP35", "IBEX 35"), ("JP225", "Nikkei 225"), ("AUS200", "ASX 200"),
        ("HK50", "Hang Seng"),
    ],
    "Divisas": [
        ("EURUSD", "Euro / Dólar"), ("GBPUSD", "Libra / Dólar"),
        ("USDJPY", "Dólar / Yen"), ("USDCHF", "Dólar / Franco"),
        ("AUDUSD", "Dólar Aus. / Dólar"), ("USDCAD", "Dólar / Dólar Can."),
        ("NZDUSD", "Dólar NZ / Dólar"), ("EURJPY", "Euro / Yen"),
        ("EURGBP", "Euro / Libra"), ("GBPJPY", "Libra / Yen"),
    ],
    "Materias primas": [
        ("XAUUSD", "Oro"), ("XAGUSD", "Plata"), ("USOIL", "Petróleo WTI"),
        ("UKOIL", "Petróleo Brent"), ("NGAS", "Gas Natural"),
        ("XPTUSD", "Platino"), ("XPDUSD", "Paladio"),
    ],
    "Criptomonedas": [
        ("BTCUSD", "Bitcoin"), ("ETHUSD", "Ethereum"), ("XRPUSD", "XRP"),
        ("LTCUSD", "Litecoin"), ("SOLUSD", "Solana"), ("ADAUSD", "Cardano"),
        ("DOGUSD", "Dogecoin"), ("BNBUSD", "BNB"),
    ],
    "Acciones": [
        ("AAPL", "Apple"), ("MSFT", "Microsoft"), ("TSLA", "Tesla"),
        ("NVDA", "NVIDIA"), ("AMZN", "Amazon"), ("GOOGL", "Alphabet"),
        ("META", "Meta"), ("NFLX", "Netflix"), ("AMD", "AMD"), ("KO", "Coca-Cola"),
    ],
}

_CSS = """
<style>
  .mkt-title { color:#e6edf3; font-size:22px; font-weight:800; margin:0; }
  .mkt-sub { color:#8b949e; font-size:13px; margin:2px 0 12px; }
  table.mkt { width:100%; border-collapse:collapse; font-size:13px; }
  table.mkt th { color:#8b949e; font-weight:600; text-align:left; padding:9px 12px;
                 border-bottom:1px solid #1f2630; font-size:12px; }
  table.mkt th.r, table.mkt td.r { text-align:right;
                 font-family:ui-monospace,Consolas,monospace; font-variant-numeric:tabular-nums; }
  table.mkt td { color:#e6edf3; padding:9px 12px; border-bottom:1px solid #141a22; }
  table.mkt tbody tr:hover td { background:#0f1620; }
  .mkt-nm { display:flex; align-items:center; gap:9px; }
  .mkt-ic { width:22px; height:22px; border-radius:50%; background:#161b22;
            display:inline-flex; align-items:center; justify-content:center;
            overflow:hidden; flex:0 0 auto; }
  .mkt-up { color:#3fb950; }
  .mkt-down { color:#f85149; }
</style>
"""


def _fila(sym: str, label: str):
    """Datos de una fila desde MT5, o None si el símbolo no existe en el bróker."""
    real = resolver_simbolo(sym)
    try:
        mt5.symbol_select(real, True)
        info = mt5.symbol_info(real)
    except Exception:
        info = None
    if info is None:
        return None
    tick = mt5.symbol_info_tick(real)

    def g(attr):
        return getattr(info, attr, 0) or 0

    last = 0.0
    if tick is not None:
        last = tick.last if getattr(tick, "last", 0) > 0 else getattr(tick, "bid", 0)
    if last <= 0:
        last = g("bid") or g("last")
    if last <= 0:
        return None

    high = g("bidhigh") or g("lasthigh") or g("high")
    low = g("bidlow") or g("lastlow") or g("low")
    ref = g("session_open") or last          # referencia para la variación del día
    var = last - ref
    pct = (var / ref * 100) if ref else 0.0
    dig = int(g("digits") or 2)
    t = int(g("time") or 0)
    hora = datetime.fromtimestamp(t).strftime("%H:%M:%S") if t else "—"

    return {
        "sym": real, "label": label, "last": last, "high": high or last,
        "low": low or last, "var": var, "pct": pct, "dig": dig, "hora": hora,
    }


def _tabla_html(categoria: str) -> str:
    filas = []
    for sym, label in _CATALOGO.get(categoria, []):
        f = _fila(sym, label)
        if f:
            filas.append(f)

    if not filas:
        return ("<div style='color:#8b949e; padding:20px 4px;'>No hay datos para esta "
                "categoría. Verifica que MetaTrader 5 esté abierto y que el bróker tenga "
                "estos instrumentos.</div>")

    cuerpo = []
    for f in filas:
        d = f["dig"]
        cls = "mkt-up" if f["var"] >= 0 else "mkt-down"
        cuerpo.append(
            "<tr>"
            f"<td><div class='mkt-nm'><span class='mkt-ic'>{icono_activo(f['sym'])}</span>"
            f"<span><b>{f['label']}</b></span></div></td>"
            f"<td class='r'>{f['last']:,.{d}f}</td>"
            f"<td class='r'>{f['high']:,.{d}f}</td>"
            f"<td class='r'>{f['low']:,.{d}f}</td>"
            f"<td class='r {cls}'>{f['var']:+,.{d}f}</td>"
            f"<td class='r {cls}'>{f['pct']:+.2f}%</td>"
            f"<td class='r' style='color:#8b949e;'>{f['hora']}</td>"
            "</tr>"
        )
    return (
        "<table class='mkt'><thead><tr>"
        "<th>Nombre</th><th class='r'>Último</th><th class='r'>Máximo</th>"
        "<th class='r'>Mínimo</th><th class='r'>Var.</th><th class='r'>% Var.</th>"
        "<th class='r'>Hora</th>"
        "</tr></thead><tbody>" + "".join(cuerpo) + "</tbody></table>"
    )


def renderizar_panel_mercados(main=None):
    inicializar_mt5()
    st.html(_CSS)
    st.html(
        "<div class='mkt-title'>Mercados</div>"
        "<div class='mkt-sub'>Cotizaciones en tiempo real · índices, divisas, "
        "materias primas, cripto y acciones</div>"
    )

    categorias = list(_CATALOGO.keys())
    cat = st.segmented_control(
        "Categoría", categorias, default=categorias[0],
        label_visibility="collapsed", key="mkt_cat",
    ) or categorias[0]

    @st.fragment(run_every="3s")
    def _tabla_en_vivo():
        st.html(_tabla_html(cat))
        st.caption(f"Última actualización: {datetime.now().strftime('%H:%M:%S')}")

    _tabla_en_vivo()
