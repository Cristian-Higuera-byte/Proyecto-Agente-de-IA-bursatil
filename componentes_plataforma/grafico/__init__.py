"""Gráfico principal del dashboard (panel central).

Organización:
  panel.py            orquesta: cabecera de precio + gráfico + botones de cierre
  cabecera_precio.py  barra de precio en vivo (se refresca sola)
  simbolo.py          decimales y tamaño del pip de un símbolo (MT5)
  ensamblador.py      arma el HTML del gráfico juntando los fragmentos de estatico/
  estatico/           el gráfico en sí (HTML + CSS + JS), partido por temas:
      esqueleto.html  orden en que se pegan los fragmentos (líneas `@@ruta`)
      css/ html/ js/  fragmentos; los números del nombre marcan el orden
El trading desde el gráfico (líneas de posición, SL/TP, órdenes) sigue en
componentes_plataforma/posiciones_grafico.py y se inserta donde el esqueleto dice __POSICIONES_JS__.
"""
