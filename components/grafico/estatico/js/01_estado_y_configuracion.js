// [grafico] Estado global, catálogo de indicadores y configuración recordada
(function(){
  var API = __API_URL_JS__;
  var SIMBOLO = __SIMBOLO_JS__;
  var DIGITS = __DIGITS__;
  var PIP = __PIP__;

  var PF = { type: 'price', precision: DIGITS, minMove: Math.pow(10, -DIGITS) };

  var tfActual = "H1";
  var nBarrasActual = 1500;
  var tipoActual = "candlestick";
  var datosActuales = [];

  var cargaId = 0;
  var cargando = false;
  var pollEnCurso = false;

  // Catálogo completo de indicadores disponibles
  var CATALOGO_INDICADORES = [
    { id: 'sma20', nombre: 'SMA 20 (Media Móvil Simple)', tipo: 'Superposición' },
    { id: 'sma50', nombre: 'SMA 50 (Media Móvil Simple)', tipo: 'Superposición' },
    { id: 'sma200', nombre: 'SMA 200 (Media Móvil Simple)', tipo: 'Superposición' },
    { id: 'ema20', nombre: 'EMA 20 (Media Móvil Exponencial)', tipo: 'Superposición' },
    { id: 'ema50', nombre: 'EMA 50 (Media Móvil Exponencial)', tipo: 'Superposición' },
    { id: 'bollinger', nombre: 'Bandas de Bollinger (20, 2)', tipo: 'Superposición' },
    { id: 'rsi', nombre: 'RSI (Índice de Fuerza Relativa 14)', tipo: 'Oscilador' },
    { id: 'macd', nombre: 'MACD (Convergencia/Divergencia)', tipo: 'Oscilador' },
    { id: 'atr', nombre: 'ATR (Average True Range)', tipo: 'Oscilador' },
    { id: 'stochastic', nombre: 'Oscilador Estocástico', tipo: 'Oscilador' },
    { id: 'parabolic', nombre: 'Parabolic SAR', tipo: 'Superposición' }
  ];

  var indicadores = { 
    sma20: false, sma50: false, sma200: false, 
    ema20: false, ema50: false, bollinger: false, 
    rsi: false, macd: false, atr: false, 
    stochastic: false, parabolic: false 
  };
  var seriesInd = { 
    sma20: null, sma50: null, sma200: null, 
    ema20: null, ema50: null, 
    bolsuper: null, bolmedia: null, bolinf: null,
    sar: null
  };

  var PANES = {};   // paneles de osciladores abiertos: id -> { el, chart, s }

  // Configuración del gráfico que se recuerda entre recargas del iframe (temporalidad, tipo, indicadores)
  var CFG_KEY = 'pj_grafico_cfg';
  var cfgRango = -1;   // índice del botón de rango activo (-1 = ninguno)
  var cfgComparar = [];       // símbolos comparados que se recordaron
  var listaCmpGuardada = [];  // símbolos comparados ahora mismo (los guarda guardarConfig)
  var modoComparar = false;   // hay símbolos comparados: el eje pasa a % y los indicadores sobre el precio se ocultan
  (function leerConfig(){
    try {
      var c = JSON.parse(localStorage.getItem(CFG_KEY) || 'null');
      if (!c) return;
      if (['M1','M5','M15','M30','H1','H4','D1','W1','MN1'].indexOf(c.tf) >= 0) tfActual = c.tf;
      if (typeof c.n === 'number' && c.n >= 50 && c.n <= 5000) nBarrasActual = c.n;
      if (['candlestick','hollow','bars','line','area','heikin'].indexOf(c.tipo) >= 0) tipoActual = c.tipo;
      if (typeof c.rango === 'number') cfgRango = c.rango;
      if (Array.isArray(c.cmp)) cfgComparar = c.cmp.filter(function(x){ return typeof x === 'string' && /^[A-Za-z0-9._#+\-]{1,24}$/.test(x); }).slice(0, 5);
      if (c.ind) Object.keys(indicadores).forEach(function(k){ if (c.ind[k] === true) indicadores[k] = true; });
    } catch (e) {}
  })();
  function guardarConfig(){
    try {
      var rg = -1;
      document.querySelectorAll('.tvrange').forEach(function(b, i){ if (b.classList.contains('active')) rg = i; });
      localStorage.setItem(CFG_KEY, JSON.stringify({ tf: tfActual, n: nBarrasActual, tipo: tipoActual, rango: rg, ind: indicadores, cmp: listaCmpGuardada }));
    } catch (e) {}
  }

