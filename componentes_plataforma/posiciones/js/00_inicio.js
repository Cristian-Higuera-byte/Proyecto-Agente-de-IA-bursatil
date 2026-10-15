    // ===== Trading desde el gráfico (componentes_plataforma/posiciones_grafico.py) =====
    (function(){
      var REAL = __POS_REAL__, INI = __POS_INI__;
      var POS = INI.pos || {}, ORD = INI.ord || {};
      var BID = INI.ba[0], ASK = INI.ba[1], VMIN = INI.vmin || 0.01, SM = INI.sm || 0, K = INI.k || 0;
      var OFF = INI.off || 0, EM = INI.em || 0;   // desfase hora servidor (s) y modos de caducidad
      var COMPRA = '#3fb950', VENTA = '#f85149', C_TP = '#3fb950', C_SL = '#ff8f00';
      var SEP = 56;   // px entre las etiquetas y el eje de precios (como XM)
      var NOMBRE = {tp: 'Take Profit', sl: 'Stop Loss'};
      var TIPO = {0: 'Buy', 1: 'Sell', 2: 'Buy Limit', 3: 'Sell Limit', 4: 'Buy Stop', 5: 'Sell Stop'};
      var PD = window.parent.document;

