-- Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
-- Dirección: José Joaquín Prieto #5373 -
-- San Miguel - Santiago - Chile
-- contacto.pinayjara@gmail.com
-- https://www.pinayjara.cl
-- Creado, Programado y Diseñado por Piña y Jara
-- Transportes y Servicios Ltda.


-- -------------------------------------------------------------------------------------------------------
-- ----------------------------- INICIO Piña y Jara aceptaciones_legales .SQL ----------------------------
-- -------------------------------------------------------------------------------------------------------

-- Descripción: constancia de qué documentos legales aceptó cada usuario (términos de uso, privacidad y cookies, aviso de riesgo), con su versión y la fecha. Una fila por
-- documento o función aceptado; se escribe al crear la cuenta, en la puerta de aceptación y al activar cada función, todas las filas de una aceptación en una sola sentencia. Lo usa herramientas/aceptaciones_legales.py.
-- Motor: PostgreSQL 10 o superior, tanto el de un hosting (phpPgAdmin > pestaña SQL) como Supabase (SQL Editor > New query > Run).
-- Ejecutar DESPUÉS de crear la tabla `usuarios`. Es idempotente: se puede volver a ejecutar sin perder datos.
-- OJO (V22): esta tabla es OBLIGATORIA. Sin ella (o sin sus columnas alcance y detalle) nadie puede pasar la puerta de aceptación ni activar vigilancias o copias: ejecutar este archivo ANTES de desplegar el código de V22.

-- -------------------------------------------
-- Estructura de tabla para la tabla `aceptaciones_legales` --
-- -------------------------------------------

CREATE TABLE IF NOT EXISTS aceptaciones_legales (
    id BIGSERIAL PRIMARY KEY,
    -- Usuario que aceptó; si se borra el usuario se borran sus aceptaciones.
    usuario_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    -- Documento o función aceptado: terminos, privacidad, riesgo (claves de componentes_plataforma/legal/contenido.py) o one_click, vigilancia, copytrading (herramientas/aceptaciones_legales.py).
    documento TEXT NOT NULL,
    -- Versión del documento que se aceptó (VERSION de contenido.py) y cuándo.
    version TEXT NOT NULL,
    aceptada_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- V22 de la auditoría: alcance de la aceptación (demo o real) cuando la función lo tiene, y detalle de lo aceptado (por ejemplo, el id de la vigilancia o de la estrategia copiada).
    alcance TEXT,
    detalle TEXT
);

-- Bases creadas antes de V22: agregan las dos columnas (idempotente; no hace falta dar permisos de nuevo).
ALTER TABLE aceptaciones_legales ADD COLUMN IF NOT EXISTS alcance TEXT;
ALTER TABLE aceptaciones_legales ADD COLUMN IF NOT EXISTS detalle TEXT;

CREATE INDEX IF NOT EXISTS aceptaciones_legales_usuario ON aceptaciones_legales (usuario_id, documento, aceptada_en DESC);

-- -------------------------------------------
-- Permisos en Supabase (no hace nada en otro PostgreSQL) --
-- -------------------------------------------

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
        ALTER TABLE aceptaciones_legales ENABLE ROW LEVEL SECURITY;
        GRANT ALL ON TABLE public.aceptaciones_legales TO service_role;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;
    END IF;
END $$;

-- Nota para un hosting (cPanel): las tablas nuevas no heredan permisos. Después de ejecutar este archivo, dar permisos al usuario de la base de datos de la
-- plataforma, cambiando <usuario> por su nombre (la variable POSTGRES_USUARIO del .env):
--   GRANT ALL ON ALL TABLES IN SCHEMA public TO "<usuario>";
--   GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "<usuario>";

-- Para ver quién aceptó qué (consulta de ejemplo):
--   SELECT u.email, a.documento, a.version, a.aceptada_en FROM aceptaciones_legales a JOIN usuarios u ON u.id = a.usuario_id ORDER BY a.aceptada_en DESC;

-- -------------------------------------------------------------------------------------------------------
-- ------------------------------ FIN Piña y Jara aceptaciones_legales .SQL ------------------------------
-- -------------------------------------------------------------------------------------------------------

-- Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
-- Dirección: José Joaquín Prieto #5373 -
-- San Miguel - Santiago - Chile
-- contacto.pinayjara@gmail.com
-- https://www.pinayjara.cl
-- Creado, Programado y Diseñado por Piña y Jara
-- Transportes y Servicios Ltda.
