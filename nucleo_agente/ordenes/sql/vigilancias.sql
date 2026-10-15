CREATE TABLE IF NOT EXISTS vigilancias (
    id TEXT PRIMARY KEY,
    usuario_id TEXT NOT NULL,
    simbolo TEXT NOT NULL,
    estado TEXT NOT NULL,        -- PENDIENTE_AUTORIZACION | ACTIVA | FINALIZADA | CANCELADA | EXPIRADA | ERROR
    instruccion TEXT,            -- lo que pidió el usuario, con sus palabras
    creada TEXT NOT NULL,
    expira_autorizacion TEXT,    -- hasta cuándo se puede autorizar
    autorizada TEXT,
    vence TEXT,                  -- cuándo termina sola (autorizada + duración)
    duracion_horas REAL,
    intervalo_min INTEGER,
    riesgo_pct REAL,             -- % del equity por operación (nunca más que el límite global)
    max_operaciones INTEGER,     -- aperturas máximas durante la vigilancia
    operaciones INTEGER DEFAULT 0,
    permite_cerrar INTEGER DEFAULT 1,  -- puede cerrar, por su análisis, las posiciones que ella abrió
    proximo_chequeo TEXT,
    ultimo_chequeo TEXT,
    ultimo_tick INTEGER,         -- hora del último tick visto: si no cambió, el mercado está parado y no se analiza
    ultimo_resumen TEXT,
    chequeos INTEGER DEFAULT 0,
    errores INTEGER DEFAULT 0,   -- fallos seguidos del análisis
    detalle TEXT
)
