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

### Pendiente
- Reiniciar servidor + dashboard y confirmar gráfico/buscador/acciones/etiquetas.
- DRAWDOWN −99% = historial de equity viejo (MT5) → resetear ese registro.
- Optimizar la carga del catálogo (paralelizar); quedan etiquetas "MT5" menores (diario, chat, backtest).
- Motor de precios a WebSocket; validar /workingorders y /history/transactions con operaciones reales.
- Rotar credenciales de prueba antes de producción.
- Pulir etiquetas "MT5"/"XM" restantes (badge del gráfico, barra superior, buscador, diario).
- Motor de precios a WebSocket de Capital (para volver a ticks rápidos sin chocar el límite REST).
- Validar /workingorders y /history/transactions con operaciones reales.
- Rotar las credenciales de prueba por unas seguras antes de producción.
- Validar las funciones de órdenes con una operación demo real (y el P/G del historial).
- UI: panel DOM → mostrar "no disponible"; `info_mt5.py` → estado de conexión de Capital.
- Rotar las credenciales de prueba por unas seguras antes de producción.
