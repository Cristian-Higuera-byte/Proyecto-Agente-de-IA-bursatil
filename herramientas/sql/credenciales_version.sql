-- Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
-- Dirección: José Joaquín Prieto #5373 -
-- San Miguel - Santiago - Chile
-- contacto.pinayjara@gmail.com
-- https://www.pinayjara.cl
-- Creado, Programado y Diseñado por Piña y Jara
-- Transportes y Servicios Ltda.


-- -------------------------------------------------------------------------------------------------------
-- ------------------------------ INICIO Piña y Jara credenciales_version .SQL ---------------------------
-- -------------------------------------------------------------------------------------------------------

-- Descripción: V18 de la auditoría de seguridad. Cada fila de `credenciales_bolsa` (credenciales de Capital.com de un usuario y modo) pasa a llevar una VERSIÓN que cambia cada vez que la fila se
-- guarda o se reemplaza. Los procesos del servidor (la plataforma, el servidor de precios, el motor de copias) la comparan antes de abrir una operación y periódicamente: si la versión que tienen
-- en memoria ya no es la de la base (el usuario reemplazó su API, o la quitó y volvió a poner otra), descartan la anterior en vez de seguir operando con ella.
-- La versión es un texto aleatorio (no un contador): quitar una credencial y volver a crearla produce otra versión distinta, así nunca coincide con la de antes.
-- Motor: PostgreSQL 10 o superior (phpPgAdmin > pestaña SQL). Ejecutar DESPUÉS de esquema_plataforma.sql y ANTES de actualizar el código. Es idempotente: se puede volver a ejecutar.

-- -------------------------------------------
-- Columna de versión --
-- -------------------------------------------

    -- Las filas que ya existen reciben cada una su propia versión (el valor por defecto se calcula fila por fila).
    ALTER TABLE credenciales_bolsa ADD COLUMN IF NOT EXISTS credencial_version TEXT NOT NULL DEFAULT md5(random()::text || clock_timestamp()::text);

-- -------------------------------------------
-- Disparador: nueva versión en cada actualización --
-- -------------------------------------------

    -- Descripción: además de la fecha de actualización, el disparador existente (`credenciales_bolsa_fecha`, antes de cada UPDATE) renueva la versión. Un INSERT nuevo usa el valor por defecto.
    CREATE OR REPLACE FUNCTION credenciales_bolsa_actualizado() RETURNS TRIGGER
        LANGUAGE plpgsql
        SET search_path = public AS $$
        BEGIN
            NEW.actualizado_en = now();
            NEW.credencial_version = md5(random()::text || clock_timestamp()::text);
            RETURN NEW;
        END;
        $$;

-- -------------------------------------------------------------------------------------------------------
-- ------------------------------- FIN Piña y Jara credenciales_version .SQL -----------------------------
-- -------------------------------------------------------------------------------------------------------

-- Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
-- Dirección: José Joaquín Prieto #5373 -
-- San Miguel - Santiago - Chile
-- contacto.pinayjara@gmail.com
-- https://www.pinayjara.cl
-- Creado, Programado y Diseñado por Piña y Jara
-- Transportes y Servicios Ltda.
