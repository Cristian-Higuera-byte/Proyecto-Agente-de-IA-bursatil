-- Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
-- Dirección: José Joaquín Prieto #5373 -
-- San Miguel - Santiago - Chile
-- contacto.pinayjara@gmail.com
-- https://www.pinayjara.cl
-- Creado, Programado y Diseñado por Piña y Jara
-- Transportes y Servicios Ltda.


-- -------------------------------------------------------------------------------------------------------
-- ---------------------------- INICIO Piña y Jara copytrading_cierre_pendiente .SQL ----------------------
-- -------------------------------------------------------------------------------------------------------

-- Descripción: V14 de la auditoría de seguridad. Una copia que debe cerrar posiciones (take profit, stop loss o «cerrar también mis posiciones») ya no se da por cerrada hasta confirmar
-- que no queda ninguna posición abierta: pasa por el estado `cierre_pendiente` y el motor reintenta el cierre. Esta migración agrega ese estado y tres columnas de seguimiento.
-- Motor: PostgreSQL 10 o superior (phpPgAdmin > pestaña SQL). Ejecutar DESPUÉS de copytrading.sql y ANTES de actualizar el código. Es idempotente: se puede volver a ejecutar.

-- -------------------------------------------
-- Estado nuevo en la tabla `copias` --
-- -------------------------------------------

    ALTER TABLE copias DROP CONSTRAINT IF EXISTS copias_estado_check;
    ALTER TABLE copias ADD CONSTRAINT copias_estado_check CHECK (estado IN ('activa', 'pausada', 'cierre_pendiente', 'cerrada'));

-- -------------------------------------------
-- Columnas de seguimiento del cierre --
-- -------------------------------------------

    -- Cuándo se pidió cerrar las posiciones (desde ahí corre el plazo de reintento).
    ALTER TABLE copias ADD COLUMN IF NOT EXISTS cierre_solicitado_en TIMESTAMPTZ;
    -- Cuántas veces reintentó el motor sin lograr cerrar todo.
    ALTER TABLE copias ADD COLUMN IF NOT EXISTS cierre_intentos INTEGER NOT NULL DEFAULT 0;
    -- TRUE cuando pasó el plazo y el usuario debe cerrar a mano lo que quede (se le avisa en la campana y en su cartera de copias).
    ALTER TABLE copias ADD COLUMN IF NOT EXISTS cierre_requiere_manual BOOLEAN NOT NULL DEFAULT FALSE;

-- El índice único «una copia vigente por inversor y estrategia» (estado <> 'cerrada') ya cubre `cierre_pendiente`: mientras se cierra, no se puede abrir otra copia de la misma estrategia.

-- Privilegios (por si la tabla fue creada con otro usuario): el usuario de la base que usa la plataforma.
    GRANT SELECT, INSERT, UPDATE, DELETE ON copias TO vptzmybcspqcmxjgjakx;


-- -------------------------------------------------------------------------------------------------------
-- ----------------------------- FIN Piña y Jara copytrading_cierre_pendiente .SQL -----------------------
-- -------------------------------------------------------------------------------------------------------

-- Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
-- Dirección: José Joaquín Prieto #5373 -
-- San Miguel - Santiago - Chile
-- contacto.pinayjara@gmail.com
-- https://www.pinayjara.cl
-- Creado, Programado y Diseñado por Piña y Jara
-- Transportes y Servicios Ltda.
