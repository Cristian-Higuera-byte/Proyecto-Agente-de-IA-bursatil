"""
componentes_plataforma/inicio
-----------------
Panel de Inicio (vista "Home") con diseño de panel de bróker profesional:
- Encabezado: saludo + selector de cuenta (chip) + botón "Operar".
- Tarjeta principal: equity grande, P/G flotante (pastilla) y 3 indicadores
  (Saldo, Margen libre, Margen usado). Botón de ojo para ocultar los montos.
- "Salud de la cuenta": nivel de margen con semáforo, barra de margen usado y
  datos técnicos (apalancamiento, crédito, tipo, servidor).
- Accesos rápidos (tarjetas con ícono, título, subtítulo y flecha).
- Promociones (banners sobrios) y Posiciones abiertas (tabla con íconos).

Archivos: panel.py (arma la vista), cuenta.py, posiciones.py, historial.py, modal_cuentas.py,
formato.py, datos.json (accesos y promos) y estilos.css.

Datos en vivo: los números llevan atributos data-pj-* y los pinta el feed
(componentes_plataforma/flujo_precios) con el MISMO dato que la barra superior.
"""
from componentes_plataforma.inicio.panel import renderizar_panel_inicio

__all__ = ["renderizar_panel_inicio"]
