// [grafico] Indicadores: fórmulas (SMA, EMA, Bollinger, RSI, ATR, MACD, Estocástico, SAR)
    // Funciones matemáticas para indicadores técnicos
    function calcularSMA(datos, periodo){
      var out = [];
      for (var i = periodo - 1; i < datos.length; i++){
        var suma = 0;
        for (var j = i - periodo + 1; j <= i; j++){ suma += datos[j].close; }
        out.push({ time: datos[i].time, value: suma / periodo });
      }
      return out;
    }

    function calcularEMA(datos, periodo){
      var out = [];
      var multiplicador = 2 / (periodo + 1);
      var emaPrevio = 0;
      for (var i = 0; i < datos.length; i++){
        if (i < periodo - 1) continue;
        if (i === periodo - 1) {
          var suma = 0;
          for (var j = 0; j <= i; j++) suma += datos[j].close;
          emaPrevio = suma / periodo;
          out.push({ time: datos[i].time, value: emaPrevio });
        } else {
          emaPrevio = (datos[i].close - emaPrevio) * multiplicador + emaPrevio;
          out.push({ time: datos[i].time, value: emaPrevio });
        }
      }
      return out;
    }

    function calcularBollinger(datos, periodo, desviaciones){
      var sma = calcularSMA(datos, periodo);
      var superiores = [], inferiores = [], medias = [];
      for (var i = 0; i < sma.length; i++){
        var idxDatos = i + periodo - 1;
        var sumaCuadrados = 0;
        var mediaVal = sma[i].value;
        for (var j = idxDatos - periodo + 1; j <= idxDatos; j++){
          var diff = datos[j].close - mediaVal;
          sumaCuadrados += diff * diff;
        }
        var desviacionEst = Math.sqrt(sumaCuadrados / periodo);
        var tiempo = sma[i].time;
        medias.push({ time: tiempo, value: mediaVal });
        superiores.push({ time: tiempo, value: mediaVal + (desviaciones * desviacionEst) });
        inferiores.push({ time: tiempo, value: mediaVal - (desviaciones * desviacionEst) });
      }
      return { medias: medias, superiores: superiores, inferiores: inferiores };
    }

    function rsiDesde(ganancia, perdida){
      if (perdida === 0) return ganancia === 0 ? 50 : 100;
      return 100 - (100 / (1 + ganancia / perdida));
    }

    function calcularRSI(datos, periodo){
      var out = [];
      if (datos.length <= periodo) return out;
      for (var k = 0; k < periodo; k++){ out.push({ time: datos[k].time }); }
      var ganancias = 0, perdidas = 0;
      for (var i = 1; i <= periodo; i++){
        var cambio = datos[i].close - datos[i-1].close;
        if (cambio >= 0) ganancias += cambio;
        else perdidas -= cambio;
      }
      var mediaGanancia = ganancias / periodo;
      var mediaPerdida = perdidas / periodo;
      out.push({ time: datos[periodo].time, value: rsiDesde(mediaGanancia, mediaPerdida) });
      for (var n = periodo + 1; n < datos.length; n++){
        var cam = datos[n].close - datos[n-1].close;
        var g = cam >= 0 ? cam : 0;
        var p = cam < 0 ? -cam : 0;
        mediaGanancia = (mediaGanancia * (periodo - 1) + g) / periodo;
        mediaPerdida = (mediaPerdida * (periodo - 1) + p) / periodo;
        out.push({ time: datos[n].time, value: rsiDesde(mediaGanancia, mediaPerdida) });
      }
      return out;
    }

    function calcularATR(datos, periodo){
      var out = [];
      if (datos.length <= periodo) return out;
      for (var i = 0; i < periodo; i++){ out.push({ time: datos[i].time }); }
      var trs = [];
      for (var i = 0; i < datos.length; i++){
        var d = datos[i];
        var tr = (i === 0) ? (d.high - d.low) : Math.max(d.high - d.low, Math.abs(d.high - datos[i-1].close), Math.abs(d.low - datos[i-1].close));
        trs.push(tr);
      }
      var atrPrev = 0;
      for (var i = 1; i <= periodo; i++){ atrPrev += trs[i]; }
      atrPrev /= periodo;
      out.push({ time: datos[periodo].time, value: atrPrev });
      for (var i = periodo + 1; i < datos.length; i++){
        atrPrev = (atrPrev * (periodo - 1) + trs[i]) / periodo;
        out.push({ time: datos[i].time, value: atrPrev });
      }
      return out;
    }

    function calcularMACD(datos, rapida, lenta, senal){
      var emaR = calcularEMA(datos, rapida);
      var emaL = calcularEMA(datos, lenta);
      var macdLine = [];
      var mapL = {};
      emaL.forEach(function(item){ mapL[item.time] = item.value; });
      emaR.forEach(function(item){
        if (mapL[item.time] !== undefined){
          macdLine.push({ time: item.time, value: item.value - mapL[item.time] });
        }
      });
      var mult = 2 / (senal + 1);
      var signalLine = [];
      var emaVal = 0;
      for (var i = 0; i < macdLine.length; i++){
        if (i < senal - 1) continue;
        if (i === senal - 1) {
          var suma = 0;
          for (var j = 0; j <= i; j++) suma += macdLine[j].value;
          emaVal = suma / senal;
          signalLine.push({ time: macdLine[i].time, value: emaVal });
        } else {
          emaVal = (macdLine[i].value - emaVal) * mult + emaVal;
          signalLine.push({ time: macdLine[i].time, value: emaVal });
        }
      }
      var mapM = {};
      macdLine.forEach(function(it){ mapM[it.time] = it.value; });
      var hist = signalLine.map(function(sv, i){
        var h = mapM[sv.time] - sv.value;
        var prev = i > 0 ? (mapM[signalLine[i-1].time] - signalLine[i-1].value) : 0;
        var col = h >= 0 ? (h >= prev ? 'rgba(63,185,80,0.9)' : 'rgba(63,185,80,0.45)')
                         : (h <= prev ? 'rgba(248,81,73,0.9)' : 'rgba(248,81,73,0.45)');
        return { time: sv.time, value: h, color: col };
      });
      return { macd: macdLine, signal: signalLine, hist: hist };
    }

    function mediaMovilSerie(serie, n){
      var out = [];
      for (var i = n - 1; i < serie.length; i++){
        var suma = 0;
        for (var j = i - n + 1; j <= i; j++) suma += serie[j].value;
        out.push({ time: serie[i].time, value: suma / n });
      }
      return out;
    }

    // Estocástico lento: %K bruto (periodo) suavizado con SMA(suav) y %D = SMA(sucd) de %K
    function calcularEstocastico(datos, periodo, suav, sucd){
      var bruto = [];
      for (var i = periodo - 1; i < datos.length; i++){
        var minL = datos[i].low, maxH = datos[i].high;
        for (var j = i - periodo + 1; j <= i; j++){
          if (datos[j].low < minL) minL = datos[j].low;
          if (datos[j].high > maxH) maxH = datos[j].high;
        }
        var val = (maxH - minL === 0) ? 50 : ((datos[i].close - minL) / (maxH - minL)) * 100;
        bruto.push({ time: datos[i].time, value: val });
      }
      var k = mediaMovilSerie(bruto, suav);
      return { k: k, d: mediaMovilSerie(k, sucd) };
    }

    function calcularParabolicSAR(datos){
      var out = [];
      if (datos.length < 3) return out;
      var af = 0.02, maxAf = 0.2;
      var longPos = datos[1].close > datos[0].close;
      var sar = longPos ? datos[0].low : datos[0].high;
      var ep = longPos ? datos[0].high : datos[0].low;
      for (var i = 2; i < datos.length; i++){
        sar = sar + af * (ep - sar);
        if (longPos) {
          if (datos[i].low < sar) { longPos = false; sar = ep; ep = datos[i].low; af = 0.02; }
          else {
            if (datos[i].high > ep) { ep = datos[i].high; af = Math.min(af + 0.02, maxAf); }
            if (datos[i-1].low < sar) sar = datos[i-1].low;
            if (datos[i-2].low < sar) sar = datos[i-2].low;
          }
        } else {
          if (datos[i].high > sar) { longPos = true; sar = ep; ep = datos[i].high; af = 0.02; }
          else {
            if (datos[i].low < ep) { ep = datos[i].low; af = Math.min(af + 0.02, maxAf); }
            if (datos[i-1].high > sar) sar = datos[i-1].high;
            if (datos[i-2].high > sar) sar = datos[i-2].high;
          }
        }
        out.push({ time: datos[i].time, value: sar, color: longPos ? '#3fb950' : '#f85149' });
      }
      return out;
    }

