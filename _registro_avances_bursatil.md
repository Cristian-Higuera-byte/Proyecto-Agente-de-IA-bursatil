# Registro de avances — Proyecto bursátil (para informe Word)

> Bitácora de cambios con código, para armar el informe final. Se actualiza cada sesión.

---

## 16-10-2026 — Decisión de arquitectura: migración de MT5/XM a Capital.com (API REST)

### Contexto / motivación
Se decidió cambiar la arquitectura: en lugar de depender del **terminal MetaTrader 5 de XM**
(que exige una máquina Windows con el terminal abierto y una cuenta logueada manualmente),
la plataforma se conectará al bróker vía **API REST con clave propia del usuario**.
XM **no** ofrece API pública a clientes retail; tras comparar opciones (OANDA, Alpaca, IBKR,
Tradier, Capital.com) se eligió **Capital.com** por ser forex/CFD (mismo universo: oro, índices),
tener esquema de API key + contraseña, y cuenta demo gratis.

Objetivo final: web en Python **sin terminal MT5 ni Windows obligatorio**; a futuro, multiusuario
(cada usuario con su propia API key, credenciales cifradas por usuario en Supabase).

### Estrategia técnica
Todo el dashboard habla con el bróker a través de **un solo módulo**
(`herramientas/puente_mt5.py`), importado por ~45 archivos. Plan: convertirlo en un **despachador**
que delega a un backend u otro según `PROVEEDOR` del `.env`:
```
herramientas/backends/mt5.py       (el código MT5 actual, movido tal cual)
herramientas/backends/capital.py   (NUEVO, mismo contrato, vía REST)
herramientas/puente_mt5.py         (despachador; los 45 imports NO cambian)
```

### Hecho en esta sesión
1. **`.env`**: añadidas variables de Capital.com — `PROVEEDOR`, `CAPITAL_DEMO`,
   `CAPITAL_API_KEY`, `CAPITAL_IDENTIFIER`, `CAPITAL_API_PASSWORD`.
2. **`_prueba_conexion_capital.py`** (nuevo): script de validación de la API (sesión + cuenta +
   precio del oro), con fix de `certifi` por la ruta con tildes (mismo bug SSL que yfinance).

### Prueba de conexión — EXITOSA (entorno DEMO)
```
[OK] Sesión abierta correctamente.
   - Account (USD): saldo=1000.0  disponible=1000.0
   - Gold  epic=GOLD  Bid=4161.69  Offer=4162.19  estado=TRADEABLE
```

### Aprendizajes clave de la API de Capital.com
- Auth: `POST /session` con header `X-CAP-API-KEY` + body `{identifier, password, encryptedPassword:false}`.
  Devuelve en headers `CST` y `X-SECURITY-TOKEN` (válidos 10 min).
- **La contraseña del `POST /session` es la que genera/define la propia KEY, NO la de la cuenta.**
  Si no se pone una personalizada, Capital genera una (hay que copiarla al crearla; no se recupera).
- `identifier` = correo de la cuenta (un error típico: una letra mal → `error.invalid.details` / HTTP 401).
- La API key de Capital tiene 16 caracteres (es normal, no está truncada).
- Requiere 2FA activo en la cuenta antes de generar la key.
- URLs: demo `https://demo-api-capital.backend-capital.com/api/v1`,
  real `https://api-capital.backend-capital.com/api/v1`.
- El oro es `epic=GOLD` (coincide con el alias que ya usa el proyecto).

### Backend construido — `herramientas/backends/capital.py` (16-10)
Se creó el backend completo con **los mismos nombres de función que el puente MT5**
(incluido `inicializar_mt5` y `MT5_LOCK`), para que sea un reemplazo *drop-in*.
Implementa: sesión con renovación automática (token 10 min) y reintento ante 401,
`obtener_info_cuenta`, `obtener_posiciones`, `obtener_historial`, `especs_posicion`,
`obtener_precio_actual`, `obtener_datos_historicos`, `obtener_velas_rango`,
`ejecutar_orden_mercado`, `colocar_orden_pendiente`, `cerrar_posicion`,
`modificar_sltp`, `modificar_orden`, `eliminar_orden`, `obtener_dom`, `resolver_simbolo`.
También `herramientas/backends/__init__.py`.

**Mapeos resueltos (verificados contra la API demo):**
- epics reales: oro `GOLD`, `US30`, `US100`, `US500`, `BTCUSD` (coinciden con los alias del proyecto).
- precios/velas: `GET /prices/{epic}` con bid/ask → se usa el punto medio para OHLC.
- cuenta: `GET /accounts` → balance, equity = balance + profitLoss, disponible, margen.
- órdenes: `POST /positions` y `POST /workingorders` → devuelven `dealReference` → se confirma
  con `GET /confirms/{ref}` (dealStatus ACCEPTED) para obtener el `dealId`.
- pendiente LIMIT/STOP deducido del precio vs mercado (igual que MT5).

**Prueba de lectura del backend: EXITOSA** (cuenta, precio oro, históricos H1, posiciones/historial
vacíos, DOM no disponible). Órdenes implementadas pero NO ejecutadas (colocarían trades demo reales;
requieren OK explícito o validación manual desde el dashboard).

**Aproximaciones / a validar con operación real:**
- `especs_posicion.k` ≈ `contractSize` (asume cotización en USD).
- `obtener_historial`: P/G realizado leído de forma defensiva (validar campo con un cierre real).
- `swap` por posición = 0.0 (Capital no lo expone; hay `overnightFee` a nivel de instrumento).

### Hallazgo de alcance — MT5 está acoplado más allá del puente
~26 archivos importan `MetaTrader5` directamente (constantes `TIMEFRAME_*`, `ORDER_TYPE_*`
y, en `servidor_precios/` y `nucleo_agente/ordenes/`, llamadas reales a `mt5.*`).
Por eso "apagar MT5 con un flag" NO basta con el despachador: hay que (a) un shim de
constantes MT5 sin el paquete, y (b) enrutar/retirar las llamadas `mt5.*` de esos módulos.

### Etapa 1 del desacople — DESPACHADOR (16-10) ✅
- `herramientas/puente_mt5.py` dejó de tener lógica MT5: ahora es un **despachador** que,
  según `PROVEEDOR` del .env (`mt5` | `capital`), reexporta el contrato del backend elegido.
- El código MT5 original se movió tal cual a `herramientas/backends/mt5.py` (fallback intacto).
- Los ~45 imports `from herramientas.puente_mt5 import ...` NO cambiaron; el candado compartido
  (`fuentes/mt5_fuentes` lee `herramientas.puente_mt5.MT5_LOCK`) sigue funcionando.
- **Probado:** con `PROVEEDOR=capital` lee la cuenta real por REST; con `PROVEEDOR=mt5` importa
  el backend MT5 sin lanzar el terminal. Cero regresión.

### Alcance real del desacople restante (medido)
De los archivos que importan `MetaTrader5` directo:
- **Solo constantes (6):** `mercados/piezas.py`, `mercado_datos/referencias.py`,
  `mercado_datos/sparkline.py`, `vigilancia/analisis.py`, `servidor_precios/constantes.py`,
  `servidor_precios/velas.py`.
- **Llamadas reales `mt5.*` (18):** componentes (buscador, grafico, mercados, panel_orden,
  posiciones, profundidad), `estadisticas_*`, `nucleo_agente/ordenes/*`, `vigilancia/*`,
  `servidor_precios/motor/*` y `simbolos.py`. Usan symbol_info, symbol_info_tick, account_info,
  positions_get, orders_get, history_deals_get, copy_rates_from_pos, order_calc_profit/margin,
  market_book_get, terminal_info, last_error.
- Hay además una 2ª capa (`fuentes/mt5_fuentes/`) con su propia conexión MT5 (usada por el agente).

Constantes MT5 a cubrir por el shim: TIMEFRAME_*, ORDER_TYPE_*, ORDER_TIME_*, ORDER_FILLING_*,
TRADE_ACTION_*, TRADE_RETCODE_DONE(_PARTIAL), DEAL_ENTRY_OUT, DEAL_TYPE_*, BOOK_TYPE_*,
POSITION_TYPE_BUY, SYMBOL_TRADE_MODE_FULL, ACCOUNT_TRADE_MODE_DEMO.

### Etapas 2 y 3 del desacople — SHIM MT5 sobre Capital (16-10) ✅
Paquete nuevo `proveedores/` (NO importa MetaTrader5 al cargar, para arrancar sin el paquete):
- `proveedores/selector_mt5.py`: expone `mt5` = paquete real MetaTrader5 (PROVEEDOR=mt5) o el shim
  (PROVEEDOR=capital). Los archivos solo cambiarán `import MetaTrader5 as mt5` →
  `from proveedores.selector_mt5 import mt5`.
- `proveedores/capital_mt5_compat.py`: shim con TODAS las constantes MT5 usadas (valores enteros
  reales) + primitivas sobre Capital: `initialize/shutdown/last_error/terminal_info`,
  `symbol_info/symbol_info_tick/symbol_select/symbols_get`, `account_info`,
  `positions_get/orders_get/history_deals_get`, `copy_rates_from_pos/copy_rates_range`,
  `order_calc_profit/order_calc_margin`, `order_send` (enruta apertura/cierre al backend Capital),
  `market_book_*` (vacío). Objetos imitan MT5 por atributos (info.digits, tick.bid, p.ticket...).

**Probado (ejercitado como el código real):** symbol_info (digits=2, point=0.01, tick_value=1.0,
stops_level=4), tick, account (equity/trade_mode demo), copy_rates indexable `rates[-2]['close']`,
order_calc_profit (−60 para 1 lote 4160→4100) y order_calc_margin (208 = 4160·5%). Todo OK.

**A validar en Etapa 4 / con operación real:** campos de `/workingorders` y `/history/transactions`
(leídos defensivamente); rendimiento de `symbol_info_tick` en el motor (idealmente mover a WebSocket);
`symbols_get` devuelve un set curado (la Observación de mercado completa necesitaría /marketnavigation).

### Etapa 4 del desacople — MIGRACIÓN DE IMPORTS (16-10) ✅
- **27 archivos** migrados: `import MetaTrader5 as mt5` → `from proveedores.selector_mt5 import mt5`
  (preservando indentación y comentarios). Excluidos a propósito: `backends/mt5.py` (MT5 real) y
  `proveedores/selector_mt5.py`. No queda ningún import directo de MetaTrader5 fuera de esos dos.
- **Capa del agente** `fuentes/mt5_fuentes/conexion.py` ahora respeta `PROVEEDOR`: con `capital` usa
  el shim (abre sesión REST, sin rutas de terminal); con `mt5` se conecta al terminal como antes.
  Se añadieron al shim las funciones del whitelist de solo-lectura que faltaban (version, *_total,
  history_orders_get).
- **Probado con PROVEEDOR=capital:**
  - Los 27 módulos importan sin error.
  - La capa del agente (`fuentes/mt5_fuentes`) devuelve precio, cuenta, posiciones y especificación.
  - `compileall` de todo el proyecto: sin errores de sintaxis.

**Estado:** con `PROVEEDOR=capital` la app ya NO depende del paquete MetaTrader5 ni del terminal
(salvo `backends/mt5.py`, que solo se carga con `PROVEEDOR=mt5`). Falta la verificación visual
end-to-end lanzando Streamlit (pendiente de OK del usuario).

### Detalles menores a pulir
- En la capa del agente, el campo `"fuente": "MetaTrader 5"` está hardcodeado (cosmético; diría
  "Capital.com" bajo ese proveedor).
- `symbols_get` del shim devuelve un set curado → la Observación de mercado completa necesitaría
  `/marketnavigation` de Capital.
- Validar con operaciones reales: campos de `/workingorders` y `/history/transactions`.
- Motor de precios: idealmente pasar a WebSocket de Capital (hoy sondea por REST).

### Prueba visual + incidente del terminal MT5 (16-10)
- Se lanzó el dashboard con `PROVEEDOR=capital` (puerto 8599) y el servidor de precios (8000):
  arranca, login propio (Supabase) OK, y el encabezado muestra el saldo de **Capital** ($1000 USD).
- Se observó que el **terminal MT5 se abrió**. Investigado a fondo:
  - Diagnóstico: bajo `PROVEEDOR=capital`, importar la app, el servidor y la capa del agente
    **NO** carga `MetaTrader5` ni `backends.mt5` (`_ES_CAPITAL=True`). El código Capital no abre MT5.
  - Causa real: el dashboard **previo en 8501** (config MT5 vieja) que ocupaba ese puerto.
- **Blindaje añadido** en `fuentes/mt5_fuentes/conexion.py`: `load_dotenv()` antes de leer PROVEEDOR
  (evita caer a 'mt5' por orden de import) + salvaguarda en `_conectar` que LANZA error si se intenta
  abrir el terminal bajo capital. Probado.
- Para lanzar con Capital (el `.env` ya trae `PROVEEDOR=capital`):
  `env\Scripts\python.exe -m streamlit run aplicacion.py`  (+ opcional `servidor_datos.py`).
- Intervalo de ticks subido a 1.5 s (suave con el límite REST; con MT5 puede volver a 0.25 s).
- Textos corregidos: pantalla de carga ("Conectando con el bróker…") y aviso de cuenta.

### Bugs encontrados en la prueba visual y corregidos (16-10)
- **Buscar activos crasheaba** (`AttributeError: SimpleNamespace no tiene 'description'`): el shim
  `symbols_get`/`symbol_info` no exponía `description`/`path`. Añadidos. Probado.
- **Gráfico "Cargando…"**: se diagnosticó que NO es un bug de datos — el servidor sirve las velas
  correctamente (probado `/velas/USDJPY?tf=M1&n=300` → 300 velas) y el CORS está bien (refleja el
  Origin localhost:8501). La causa: el dashboard corría con el código viejo (sin los arreglos del
  shim). Se resuelve reiniciando el dashboard.
- Mejora: shim `symbol_info` ahora expone `trade_calc_mode` (+ constante `SYMBOL_CALC_MODE_FOREX`),
  así `info_simbolo` calcula bien decimales/pip (USDJPY→3/0.01, GOLD→2). Antes se tragaba en except.
- Pendiente de datos (no bug de migración): acciones (Adidas/Nvidia) salen 0.00000 porque el shim
  `symbols_get` devuelve un set curado sin esas acciones; su epic no se resuelve. Mejorar con
  /marketnavigation o un mapa de epics de acciones. DRAWDOWN −99% = datos viejos de equity (MT5).

### Cómo reiniciar limpio (tras cambios de código)
1. Cierra el dashboard viejo (Ctrl+C) y el servidor (Ctrl+C).
2. `env\Scripts\python.exe servidor_datos.py`  (una terminal)
3. `env\Scripts\python.exe -m streamlit run aplicacion.py`  (otra terminal)
   (el .env ya trae PROVEEDOR=capital)

### Bugs de la 2ª prueba visual — corregidos (16-10)
Abrí el dashboard yo mismo (browser pane, sesión reusada) y diagnostiqué con la consola/red:
- **Gráfico "Cargando…"**: el JS pedía `/velas/...?n=1500`; Capital rechaza `max>1000`
  (`error.invalid.max`) → 0 velas. FIX: `backends/capital.py._velas_crudas` recorta `max` a 1000.
- **Buscador solo 10 activos**: el shim devolvía una lista curada. FIX: `symbols_get` ahora trae el
  catálogo real vía `/marketnavigation` (recorre grupos + 1 nivel de subnodos, cacheado 10 min):
  ~1548 instrumentos (forex, índices, materias primas, cripto, acciones, ETF...). Primera carga ~15 s
  (luego cacheada); se puede optimizar con llamadas en paralelo.
- **Acciones en 0.00000** (Adidas/Nvidia/Tesla): el nombre guardado no resolvía al epic. FIX:
  `resolver_simbolo` ahora, si el núcleo no es epic válido, busca por texto (`searchTerm`) y cachea
  (Adidas→ADSGN, Nvidia→NVDA, Tesla→TSLA, Apple→AAPL), verificado con precio real.
- **Etiquetas "XM / MT5" y "Cuenta conectada en MT5 (demo)"**: FIX: `puente_mt5.NOMBRE_PROVEEDOR`
  ("Capital.com" | "MT5 / XM") usado en `grafico/cabecera_precio.py` y `panel_orden/panel.py`.

IMPORTANTE: el recorte de velas vive en el backend que usa TAMBIÉN el servidor de precios →
reiniciar el **servidor** y el **dashboard** para que tomen todos los arreglos.

### Integración de los cambios de Cristian (merge) — 16-10
Se commiteó la migración a Capital (f5edc95) y se mergeó `origin/main` (cambios de Cristian:
favoritos a barra derecha, watchlist no desplegable, backtest con replay, cortina de transición,
velocidad, y headers de crédito en todos los archivos). Merge commit f4c845b.
**9 conflictos resueltos manteniendo AMBOS** (Capital + layout de Cristian):
- `puente_mt5.py` → se conservó el despachador (bridge MT5 vive en `backends/mt5.py`; Cristian solo
  tocó docstring/headers).
- `fuentes/mt5_fuentes/conexion.py` → rename `_lock`→`_candado` de Cristian + lógica Capital.
- `info_mt5/entrada/oco/stop_dinamico` → versión de Cristian + import vía `proveedores.selector_mt5`.
- `cabecera_precio/panel_orden` → layout de Cristian + etiqueta `NOMBRE_PROVEEDOR`.
- `vista_operativa` → layout nuevo de Cristian.
Verificado: compila todo (exit 0) y los 13 módulos clave (app + favoritos/transición/riel + servidor)
importan OK bajo Capital. Merge en LOCAL (sin push). `lista_colapsable/` quedó como código huérfano
(Cristian reemplazó el watchlist desplegable). Conflicto de stash viejo en
`_contexto_nuevo_chat/_dia17_gen_informe.py` (ajeno al merge, no afecta la app).

### Rendimiento: precios en vivo por WebSocket (16-10)
La app iba lenta porque con Capital cada tick era una llamada REST remota (vs MT5 local). Solución:
- **`servidor_precios/streaming_capital.py`** (nuevo): mantiene UNA conexión WebSocket a
  `wss://api-streaming-capital.backend-capital.com/connect`, se suscribe (`marketData.subscribe`
  con cst/securityToken del backend), guarda Bid/Ask en caché, hace ping cada 5 min y reconecta solo.
  Usa `websockets` (asyncio en hilo daemon). Máx 40 epics.
- **`motor/base.py`**: bajo Capital, `_leer_ticks` lee de la caché del WS (instantáneo) en vez de
  `mt5.symbol_info_tick` (REST). Con MT5 sin cambios.
- **`constantes.py`**: `INTERVALO_TICKS` 1.5 → 0.5 s (leer el WS es gratis). La cuenta sigue REST cada 3 s.
Resultado: se eliminan las decenas de llamadas REST/seg del tiempo real. Probado: el WS recibe precios
en vivo (GOLD/EURUSD/USDJPY/BTC) que se actualizan cada segundo. Compila y el servidor importa OK.
Para activarlo: **reiniciar el servidor** (`servidor_datos.py`).

### Rendimiento 2: batch de precios + caché de lecturas (16-10)
Diagnóstico: cada llamada REST a Capital tarda ~300-500 ms, y el dashboard re-ejecuta TODA la página
en cada interacción haciendo muchas llamadas REST (cuenta, specs, margen, DOM...) + `carga.py` pedía
el precio de CADA símbolo uno por uno (~8 s de congelada). Fixes:
- **`backends/capital.py`**: caché de lecturas (precio 3 s, cuenta 2 s, posiciones 2 s) + nueva
  `precargar_precios(symbols)` que pide VARIOS precios en 1 llamada (`GET /markets?epics=...`, máx 50).
- **`puente_mt5.py`**: exporta `precargar_precios` (no-op en MT5).
- **`carga.py`**: llama `precargar_precios(simbolos)` antes del bucle → 1 llamada en vez de N.
- **shim `_TTL_MERCADO`** 2 s → 30 s (specs estáticas; el bid/ask de display viene por SSE/WS).
Medido: cargar 8 precios pasó de **3132 ms → 276 ms**; re-render cacheado **0 ms**.
NOTA: la caché es por proceso (no por usuario); al ir a multiusuario habrá que hacerla por usuario.

### Rendimiento 3: buscador instantáneo (16-10)
El buscador tardaba ~15 s porque el catálogo se armaba con ~60 llamadas `/marketnavigation` EN SERIE.
Fix en `proveedores/capital_mt5_compat.py._catalogo`:
- Recorrido EN PARALELO (ThreadPoolExecutor, `_nav` sin candado) + reintento paralelo de subnodos vacíos.
- **Caché en disco** `data/catalogo_capital.json` (TTL 24 h): tras la 1ª carga, abre en ~33 ms.
Medido: 1ª vez ~5 s (antes 15.8 s); desde disco **33 ms** con 1586 instrumentos.

### Diario (trading journal) con Capital — limitación encontrada (16-10)
El Diario (`estadisticas_diario.calcular()`) reconstruye operaciones **emparejando deals IN+OUT de MT5
por position_id** (entrada/salida, duración, R/R). Capital NO da esa estructura: su
`/history/transactions` solo trae "Trade closed" con instrumentName, size/monto, fecha, dealId (sin
precios de entrada/salida ni P/L desglosado claro); `/history/activity` vino vacío. Por eso el Diario
queda vacío bajo Capital. La cuenta demo además solo tiene 1 cierre (GOLD, hoy).
PENDIENTE: adaptar el Diario a Capital = diario BÁSICO desde `obtener_historial` (símbolo, P/L, fecha);
los datos ricos de MT5 (entrada/salida exactas, R/R) no estarán o serán aproximados. Nota: el campo
de P/L en la transacción Capital es ambiguo (`size` podría ser el monto); validar con más cierres.

### Diario adaptado a Capital (16-10) ✅
`herramientas/estadisticas_diario.py`: `operaciones()` ahora es provider-aware. Bajo Capital usa
`_operaciones_capital()` que arma el diario desde `obtener_historial` (símbolo, P/L=`neto`, fecha),
con las mismas claves que espera la UI; `estadisticas()` calcula igual (win rate, profit factor, P&L,
drawdown). Campos sin dato en Capital (entrada/salida, duración, R/R) quedan neutros (0/None/"—").
Textos de UI: subtítulo neutral y nota al pie provider-aware (explica la limitación de Capital).
Probado: muestra la operación GOLD cerrada (+0.13, win rate 100%). Compila e importa OK.
Confirmado: en Capital el monto del cierre en `/history/transactions` (`size`) ES el P/L (el balance
subió exactamente ese monto).
FIX mini-gráfico: con `hora_in=0` el rango de velas daba inicio negativo → `datetime.fromtimestamp`
reventaba en Windows (OSError 22). Ahora `_operaciones_capital` usa `hora_in=hora_out` (duración 0) y
`obtener_velas_rango` se blindó contra timestamps <=0 (clamp). El mini-gráfico muestra ~11 velas
alrededor del cierre.

### Resumen (portafolio) con Capital — correcciones (16-10)
- **Drawdown -99.2%**: era el equity viejo de XM en `data/equity.json` (4523 muestras, pico $133,164).
  Reseteado a `{"puntos":[]}` (respaldo `data/equity_xm_viejo.json.bak`). El drawdown se reconstruye
  desde los ~$1000 de Capital (el motor va registrando). Afectaba también la barra superior.
- **P&L realizado +0.00 pese a "1 cierre"**: el shim `history_deals_get` no usaba `size` como P/L (el
  backend `obtener_historial` sí, por eso el Diario sí lo mostraba). FIX: shim usa
  `profitAndLoss or pnl or size`. Ahora realizado = +0.13.
- **Depósito inicial 0.00 / Rentabilidad 0.00%**: Capital no genera "deal de balance" y su campo
  `deposit` refleja el balance actual (no el inicial). FIX en `estadisticas_portafolio`: depósito
  inicial = balance − P/L realizado acumulado (asume sin depósitos/retiros) = 1000.00; rentabilidad
  = +0.13 (+0.0130%). (También se añadió `deposito` a `obtener_info_cuenta` como dato de respaldo.)
Los demás ceros (exposición, riesgo, comisiones, flotante) son correctos: no hay posiciones abiertas.
PENDIENTE multiusuario: el depósito reconstruido asume sin depósitos/retiros; con cuentas reales habrá
que usar el historial de movimientos real.

### Cierre del Día 19 (16-10-2026)
- **Commiteado y pusheado a `main`.** `main` remoto quedó en `edd73b5` (fast-forward desde `ca65cf0`):
  migración Capital (f5edc95) + merge de Cristian (f4c845b) + WebSocket/rendimiento/vistas (edd73b5).
- Informe del día generado (Día 19) en `OCTUBRE/16-10-2026/`. Guía de creación de cuenta + API del
  usuario corregida (frases + estilo, 32 imágenes conservadas).
- Scripts de prueba (`_prueba_*.py`, `_descubrir_capital.py`) y `data/` no versionados a propósito.

### Pendientes (consolidados al cierre del Día 19)
1. Pulir etiquetas/textos menores que aún nombran "MT5"/"XM" en la UI (badge del gráfico, barra
   superior, buscador, diario, backtest, chat) → provider-aware.
2. Validar las funciones de órdenes (abrir/cerrar/pendientes/SL-TP) con operaciones demo reales en
   Capital; confirmar los campos de `/workingorders` y el P/L del historial con más cierres.
3. Afinar aproximaciones del backend Capital: `especs_posicion.k` y swap (para la Cartera).
4. Multicliente: almacenamiento por usuario (equity, journal, credenciales de API cifradas) en Supabase;
   el depósito reconstruido (balance − P/L) asume sin depósitos/retiros → usar historial real.
5. Cobertura del catálogo del buscador (categorías) y set curado de respaldo.
6. Rotar las credenciales de prueba por unas seguras antes de producción.
7. Opcional: capturas del dashboard con Capital para el informe.


## 19-10-2026 — Día 20: validación de operaciones en Capital.com, rendimiento, estándar de código y merge con Cristian

### Operaciones sobre Capital.com (diferencias frente a MT5)
- **Cancelar/modificar órdenes pendientes:** Capital identifica cada orden con un texto largo (dealId) y la interfaz lo
  convertía a entero. Se creó `herramientas/tickets.py` (acepta ambos formatos) y se ajustó el JS que envía la cancelación.
- **Lotes:** Capital mide en unidades (FX: 1 lote = 100.000). Se agregó el factor de lote por instrumento
  (`factor_lote`, `factor_lote_epic`) y se aplica en cartera, ticket e historial (0,01 lote ya no aparece como 100).
- **SL/TP:** cada PUT reemplaza ambos niveles; `modificar_sltp`/`modificar_orden` leen el nivel vigente y lo reenvían, así se
  puede quitar solo uno. Validación del **stop dinámico** (distancia mínima del bróker) con mensaje claro.
- **Capital/margen y hora:** el `balance` ya incluye el P/L abierto (no se cuenta dos veces); la hora se pasa a hora local.
- **OCO:** se adaptó el identificador del par. **PENDIENTE:** el botón verde de OCO no responde en algunas pruebas.

### Rendimiento y vistas
- Se quitó el candado global de consultas (serializaba REST), caché con refresco en segundo plano (`_cache_con_refresco`),
  caché de proceso (`herramientas/cache_proceso.py`) y **precarga** de todas las pestañas. Modal de cierre instantáneo y
  cifras del modal en vivo; etiqueta de precio alineada con la línea del gráfico.
- **Mercados:** logos de instrumentos (incluye acciones), arranca con el primer activo de la lista. **Diario:** reconstruido con
  `/history/activity` (ventanas de 24 h): lotes, entrada, salida y duración. **DOM nivel 1** (mejor bid/ask, spread y cinta
  de cotizaciones, `profundidad_mercado/nivel1.py`, ruta `/dom/<sym>`). Campo del Diario ya no editable.

### Estándar de código de la empresa (referencia: menu.php + notas de la reunión)
- Cabecera de créditos, banner INICIO/FIN y pie en cada archivo; `# TITULO` por función/clase (Python, JS y CSS); descripción
  (docstring) en cada función; comentarios sobrantes retirados.
- **Fachadas eliminadas** de `componentes_plataforma/` (19 archivos que solo reexportaban); imports reescritos.
- **Nombres en español sin abreviar** (solo trading en inglés), por fases: A (~940 nombres compartidos Python/CSS/JS), B
  (variables y parámetros), B2 (funciones y constantes) y C (JS, ~380 identificadores). Verificado con un banco de pruebas en el
  navegador (reglas CSS, errores de consola, recorrido de vistas). Excepciones: API de MT5 (`capital_mt5_compat.py`),
  herramientas del agente, claves de protocolo servidor↔JS y propiedades JS. Detalle en la memoria `nombres-en-espanol`.
- **Bug por renombrado corregido:** las tarjetas de campo del ticket (volumen, SL, TP, calculadora de riesgo) perdieron su estilo
  porque `ord_bx`/`ord_box` chocaron; el CSS apuntaba a `orden_zona_` en vez de `orden_caja_` (`ticket.css`). Reiniciar Streamlit
  (el CSS se lee una vez con `lru_cache`).

### Merge con los cambios de Cristian (`origin/main` = `05112ad`)
- Su commit toca 22 archivos (noticias con lectura interna, serie de velas en memoria, sesión compartida y limitador de
  peticiones en `capital.py`, `paralelo.py`, `velas.py`). Se guardó lo nuestro en un commit (`0d4568d`) y se fusionó: 28
  conflictos en 9 archivos; en `capital.py`, `rss.py`, `velas.py` y `noticias/secciones.py` se tomó su versión y se le aplicaron
  nuestros nombres (fases A/B/B2). Se unificaron `_ORDEN_CANDADO`, `_CANDADO_SESION` y `_medio`; se agregaron descripciones
  a las funciones nuevas. Verificado: compila, sin nombres indefinidos, módulos principales se importan.
- **Subido a `main`: `ab23724`** (merge). No probado corriendo en pantalla todavía.

### Documentos de la práctica (carpeta `C:\Practica\Informe Practica Profesional\`)
- Informe de práctica (14 páginas) y bitácora Duoc UC rellenados; datos tomados del formulario de validación. Informe del Día 20
  generado en `OCTUBRE/19-10-2026/`.

### Pendientes (al cierre del Día 20)
1. **Probar en pantalla el código fusionado** (reiniciar Streamlit y servidor): Noticias, Mercados, gráfico (W1, backtest hasta
   20.000 velas), cancelación de órdenes, ticket (campos).
2. Botón verde de **OCO** sin respuesta (pedir detalle: ¿no pasa nada o hay error?).
3. Renombrado restante: atributos de clase, propiedades JS, clases CSS de una palabra y JS embebido en cadenas de Python.
4. Avisar a Cristian: al traer `main` recibirá cambios en casi todos los archivos (nombres nuevos).
5. Los pendientes 1 a 6 del Día 19 siguen vigentes (etiquetas MT5, validar órdenes, aproximaciones, multicliente, catálogo,
   credenciales). Idea evaluada: **copytrading** con copiador propio sobre la API de Capital (retraso de 1 a 2 s, tope de
   peticiones, revisión CMF); prototipo con dos cuentas demo.

## 20-10-2026 — Día 21: preparación multiusuario (cuentas Capital.com por usuario, real y demo) y nuevo proyecto Supabase

### Indicador "Mercado" de la barra superior con Capital
- **Hallazgo:** `_mercado_abierto` (herramientas/estadisticas_portafolio.py) decidía por avance del tick entre dos lecturas. Con Capital el tick del shim siempre lleva la hora actual y la primera lectura devuelve "sin dato"; como la barra solo se redibuja con un rerun, quedaba en "—".
- **Solución:** con `PROVEEDOR=capital` se lee el estado de sesión que informa Capital (`marketStatus` → `symbol_info().trade_mode`). Con MT5 queda el método anterior.

### Análisis: qué hay que revisar para lanzar a muchos usuarios (checklist en 6 bloques)
- Arquitectura (cuenta por usuario, estado global, servidor de precios, almacenes locales), seguridad, fiabilidad/rendimiento, despliegue, funcional y legal/negocio. Se decidió cada usuario con SUS cuentas de Capital (real y demo) y elección tipo Capital.com, pensando en dinero real desde el diseño (no versión solo demo).
- **Hallazgo:** el backend `capital.py` asumía una sola cuenta (credenciales del `.env` en constantes del módulo, tokens, cachés y límite de peticiones globales).

### Nuevo proyecto Supabase `pyj-bursatil-plataforma` (separado de los otros proyectos)
- Creado en plan Free, región Americas, con "Automatically expose new tables" desactivado y RLS automático activado. Tablas: `usuarios`, `watchlist_usuario`, `credenciales_bolsa` (SQL con el estándar P&J en `herramientas/sql/esquema_plataforma.sql`).
- **Hallazgo:** al desactivar la exposición automática las tablas nacen sin permisos y el servidor falló con `42501 permission denied`; se agregó `GRANT ... TO service_role` (solo ese rol; `anon` y `authenticated` siguen sin acceso). Quedó en el SQL.
- Los `.sql` siguen ahora el estándar P&J (créditos, banner INICIO/FIN, títulos y descripciones; referencia en `ORDENAMIENTO ARCHIVOS`).

### Paso 1 — Credenciales cifradas (`herramientas/credenciales_bolsa.py`)
- Cada dato (correo, API key y contraseña de la key) se cifra con Fernet antes de salir del servidor; clave maestra en `CREDENCIALES_CLAVES` (una o varias, la primera cifra y todas descifran → rotación con `recifrar_todas()`).
- Una fila por usuario y modo: `PRIMARY KEY (usuario_id, es_demo)`. `estado_credenciales()` devuelve solo `{"demo": bool, "real": bool}`, nunca secretos.

### Paso 2 — Sesión de Capital por usuario (sin reescribir el núcleo)
- `capital.py` pasó a `capital_nucleo.py` (misma lógica; solo se quitaron del log fragmentos de la API key). `sesiones_capital.py` carga una COPIA independiente del núcleo por cada (usuario, modo) con `importlib`; cada copia tiene sus credenciales, tokens, cachés, límite de peticiones y archivo de sesión. `capital.py` es ahora una fachada (`__getattr__` de módulo) que enruta cada llamada a la copia del usuario actual → los ~45 archivos que lo usan no cambian.
- Usuario actual: `con_clave()` (hilos/servidor) → resolvedor de la sesión de Streamlit → sin usuario: cuenta del `.env` si `CAPITAL_MULTIUSUARIO` está apagado, o copia SIN cuenta ("sin conexión") si está encendido.
```python
def clave_actual() -> tuple:
    if not MULTIUSUARIO:
        return _CLAVE_LEGADO       # un solo usuario: siempre la cuenta del .env
    ...
```
- **Hallazgo (error propio):** con el modo apagado el resolvedor igual identificaba al usuario y el backend buscaba credenciales inexistentes → "sin conexión" aun con la sesión del `.env` viva. Corregido (con el modo apagado se ignora al usuario).

### Paso 3 — Pantalla "Conectar mi cuenta" y selector real/demo
- Paquete `componentes_plataforma/conectar_cuenta/` (`modo.py`, `pantalla.py`, `menu.py`): tras el login, sin cuenta conectada se muestra el formulario (tipo Demo/Real, correo, API key, contraseña de la key; la real exige confirmar que opera con dinero real); antes de guardar se verifica contra Capital (`probar_credenciales`, abre y cierra una sesión de prueba). Menú del usuario: "Cambiar a cuenta Real/Demo" y "Mis cuentas"; etiqueta DEMO (azul) / REAL (roja) siempre visible.
- Seguridad por defecto: al entrar o recargar se parte SIEMPRE en demo.
- **Hallazgo:** una marca de plantilla vacía en una línea propia de `usuario_menu.html` dejaba una línea en blanco; Markdown cortaba el bloque HTML y el menú se veía como código. La marca quedó pegada a la línea del separador.

### Paso 4 — Servidor de precios y procesos por usuario
- **Hallazgo de diseño:** el servidor de datos es otro proceso y no ve la sesión de Streamlit (vive en memoria) → token firmado. `herramientas/token_datos.py`: HMAC-SHA256 con `SERVIDOR_SECRETO`, vigencia 12 h, `{u, d, e}`; viaja dentro de la dirección base (`<servidor>/t/<token>`), así los más de 15 `fetch` de los scripts del navegador no cambian. Prueba: una firma con caracteres no ASCII lanzaba excepción en vez de rechazarse (corregido comparando bytes).
- **Almacenes por usuario** (`herramientas/carpeta_usuario.py`): equity, cerradas, diario, OCO y stop dinámico pasan de `data/` a `data/usuarios/<id>/<demo|real>/` (en modo de un solo usuario siguen en `data/`). Cambio uniforme en los 5 almacenes (`_RUTA`/`_DIR` → `ruta_archivo()`/`carpeta_usuario()`).
- **Un motor y un stream de precios por cuenta** (`servidor_precios/motor/registro.py`, `streaming_capital.stream_de()`): cada motor corre con la sesión de su usuario, se apaga a los 300 s sin clientes ni vigilancias, y un hilo (`descubrir()`) vuelve a encender el de toda cuenta con stop dinámico u OCO activos (deben seguir funcionando con el navegador cerrado).
- **Manejador HTTP:** `_identificar()` valida el token (401 sin token válido; `/salud` pública) y ejecuta cada GET/POST dentro de `con_clave(...)`; orígenes permitidos configurables (`SERVIDOR_ORIGENES`).
- **Hilos:** `herramientas/hilos.py` (`lanzar_hilo`, `enviar_al_pool`, `con_usuario`): un hilo o pool nuevo NO hereda al usuario. Aplicado en velas, caché de proceso, turnos del agente, mercados, diario y navegación del shim. Las vigilancias del agente corren con la cuenta DEMO de su dueño. Último error de orden del shim ahora por hilo. La precarga global de Mercados se omite en modo multiusuario.
- **Verificación:** pruebas sin red de aislamiento de copias, token, almacenes, hilos y servidor HTTP real en puerto de prueba (sin token → 401, token inválido → 401, orden sin token → 401, un motor por cuenta); todo el proyecto compila. NO se probó en pantalla ni contra Capital con varios usuarios.

### Pendientes para encender el modo multiusuario
1. `.env` del servidor: `CAPITAL_MULTIUSUARIO=true`, `SERVIDOR_SECRETO` (≥ 32 caracteres), `CREDENCIALES_CLAVES`; después retirar las claves de Capital del `.env`.
2. Probar en pantalla con dos usuarios (demo y real) y reiniciar servidor y Streamlit.
3. Hosting: proxy HTTPS, dominio, `MT5_API_URL` público y `SERVIDOR_ORIGENES`; el token de datos viaja en la URL → solo por HTTPS.
4. Sesiones de Streamlit (`almacen_sesiones`) son en memoria: no sobreviven a un reinicio ni a varios procesos.
5. Datos aún globales: `consultas_guardadas.json`, `alertas_activas.json`, `one_click_aceptaciones.json`, `ordenes.db`, archivos de epics y cierres compartidos entre copias.
6. Límites de seguridad por usuario en el servidor (tamaño máximo de orden, interruptor de corte) y registro de auditoría de operaciones.
7. Revisión legal CMF antes de abrir al público con cuentas reales.

### Merge con los cambios de Cristian (`origin/main` = `84db9fd`, 5 commits) sobre el trabajo multiusuario
- **Método:** respaldo del trabajo (parche + archivos nuevos en el scratchpad), `git stash` de lo rastreado, `git merge --ff-only origin/main` (sin conflictos: 58 archivos de Cristian) y `git stash pop`. Tres conflictos, los tres resueltos conservando ambos lados.
- **`capital.py` (conflicto de fondo):** Cristian agregó `detalle_operacion` (detalle rápido de una operación cerrada para el agente) al `capital.py` monolítico, que aquí ya es la fachada. Se dejó nuestra fachada y la función se pasó a `capital_nucleo.py`; la fachada la entrega por `__getattr__` (el agente la usa como `cap.detalle_operacion`).
- **Barra superior y menú del usuario:** se conservaron los enlaces de Perfil y Configuración de Cristian (con `__TOKEN__` y escape HTML) y nuestras entradas de cuentas (`__ENTRADAS_CUENTA__`) y la etiqueta DEMO/REAL.
- **Perfil de usuario (nuevo de Cristian):** tabla `perfiles_usuario` con datos personales (documento, teléfono, dirección). Se creó en el Supabase nuevo con RLS y permisos solo para `service_role` (comprobado: las 4 tablas con RLS activo, el servidor escribe, `anon` no lee). Registrado en `esquema_plataforma.sql`.
- **Revisión de compatibilidad:** el resto de lo nuevo (accesos internos `cap._epoch_utc`, `cap._datos_mensuales`, aceptaciones de vigilancia por usuario en `data/vigilancia_aceptaciones.json`) funciona con la fachada sin cambios. `perfiles_locales.json` solo se usa sin Supabase.
- **Hallazgo:** `data/usuarios/` y `data/sesiones_capital/` NO estaban en `.gitignore` (un `git add .` habría subido datos de usuarios y tokens de sesión); se agregaron.
- **Verificación:** todo el proyecto compila, imports de la app y de `servidor_precios` correctos, y las pruebas sin red del multiusuario (aislamiento, token, hilos, servidor HTTP, verificación de ambas cuentas) siguen pasando. No se probó en pantalla. Nada de commit ni push (no se pidió).
