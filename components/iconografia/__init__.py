"""
components/iconografia
----------------------
Íconos de activos con el estilo de las plataformas de trading (tipo XM), en UN
solo lugar para todo el dashboard (Lista de activos, Favoritos, Cartera,
Cotizaciones).

Reglas según el tipo de activo:
  - Divisas (EURUSD, USDJPY…): dos banderas REDONDAS superpuestas
    (moneda base adelante a la izquierda, moneda cotizada atrás a la derecha).
  - Cripto (BTCUSD, ETHUSD…): logo de la cripto + bandera de la moneda cotizada.
  - Índices (US30Cash, JP225Cash…): bandera redonda del país + etiqueta abajo.
  - Materias primas (GOLD, SILVER, OILCash…): ícono propio (SVG) en círculo de color.
  - Acciones (NVDA.OQ…): logo de la empresa sobre un círculo con sus iniciales
    (si el logo no existe, quedan visibles las iniciales).
  - Cualquier otro: iniciales en un círculo de color estable.

Fuentes (uso libre): banderas redondas "circle-flags" (HatScripts, MIT) y logos
de cripto "cryptocurrency-icons" (CC0), ambas por CDN jsDelivr. Los íconos de
materias primas son SVG propios. NO se usan archivos de XM (son su propiedad).

El HTML usa solo estilos en línea e <img> (st.html sanea el SVG en línea, por eso
los SVG propios van como imagen data-URI).
"""
from components.iconografia.icono import icono_activo

__all__ = ["icono_activo"]
