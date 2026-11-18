-- Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
-- Dirección: José Joaquín Prieto #5373 -
-- San Miguel - Santiago - Chile
-- contacto.pinayjara@gmail.com
-- https://www.pinayjara.cl
-- Creado, Programado y Diseñado por Piña y Jara
-- Transportes y Servicios Ltda.


-- -------------------------------------------------------------------------------------------------------
-- ------------------------- INICIO Piña y Jara liquidaciones_y_billetera_atomicas .SQL ------------------
-- -------------------------------------------------------------------------------------------------------

-- Descripción: V15 de la auditoría de seguridad. (1) La liquidación de la comisión de rendimiento pasa a una función que bloquea la copia, calcula con la marca de agua vigente y la adelanta
-- en la misma operación, con un período canónico (el mismo para cualquier trabajador) y una clave de pago derivada de ese período: dos trabajadores sobre la misma copia y período producen
-- UNA sola liquidación y UN solo cobro. (2) Las recargas de la billetera comprueban el saldo máximo y el tope mensual DENTRO de la transacción que bloquea la billetera. (3) Las compras de
-- plan con la billetera dejan su estado guardado (iniciada, cobrada, activada, reembolsada o cancelada) para poder retomarlas si el proceso se interrumpe entre cobrar y activar.
-- Motor: PostgreSQL 10 o superior (phpPgAdmin > pestaña SQL). Ejecutar DESPUÉS de billetera.sql, copytrading.sql y copytrading_comisiones.sql, y ANTES de actualizar el código.
-- Es idempotente: se puede volver a ejecutar sin perder datos.

-- -------------------------------------------
-- Clave de pago de cada liquidación --
-- -------------------------------------------

    -- Identidad del pago de la liquidación (copia + período), usada como clave de idempotencia de la transferencia; vacía en las liquidaciones anteriores a V15 (usan la clave antigua por id).
    ALTER TABLE comisiones_rendimiento ADD COLUMN IF NOT EXISTS clave_pago TEXT;
    CREATE UNIQUE INDEX IF NOT EXISTS comisiones_clave_pago ON comisiones_rendimiento (clave_pago) WHERE clave_pago IS NOT NULL;

-- -------------------------------------------
-- Función `comision_liquidar` --
-- -------------------------------------------

    -- Descripción: liquida UN período de una copia de forma atómica. Bloquea la fila de la copia (dos trabajadores se turnan), devuelve la liquidación existente si ese período ya se liquidó
    -- (`out_nueva` falso), y si no calcula la comisión sobre la ganancia que supera la marca de agua, guarda la liquidación, ADELANTA la marca de agua y, si es la final, anota `comision_final_en`.
    -- El cobro (transferencia entre billeteras) lo hace después la plataforma con `out_clave_pago`; como la marca avanza aquí, una comisión pendiente de cobro no se vuelve a calcular.
    -- `p_hasta` es el fin canónico del período: el mismo valor para cualquier trabajador. No devuelve filas si no hay nada que liquidar (final ya hecha, o período anterior al último liquidado).
    CREATE OR REPLACE FUNCTION comision_liquidar(p_copia BIGINT, p_hasta TIMESTAMPTZ, p_final BOOLEAN DEFAULT FALSE)
    RETURNS TABLE (out_id BIGINT, out_nueva BOOLEAN, out_comision NUMERIC, out_marca_despues NUMERIC, out_clave_pago TEXT, out_movimiento_id BIGINT)
    LANGUAGE plpgsql AS $$
    DECLARE
        v_copia copias%ROWTYPE;
        v_fila comisiones_rendimiento%ROWTYPE;
        v_pct NUMERIC;
        v_ganancia NUMERIC;
        v_marca NUMERIC;
        v_nueva_marca NUMERIC;
        v_desde TIMESTAMPTZ;
        v_hasta TIMESTAMPTZ;
        v_comision NUMERIC;
        v_clave TEXT;
        v_id BIGINT;
    BEGIN
        SELECT c.* INTO v_copia FROM copias c WHERE c.id = p_copia FOR UPDATE;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'copia_inexistente';
        END IF;
        IF p_final AND v_copia.comision_final_en IS NOT NULL THEN
            RETURN;
        END IF;
        SELECT r.* INTO v_fila FROM comisiones_rendimiento r WHERE r.copia_id = p_copia AND r.periodo_hasta = p_hasta;
        IF FOUND THEN
            IF p_final THEN
                UPDATE copias SET comision_final_en = now() WHERE id = p_copia;
            END IF;
            RETURN QUERY SELECT v_fila.id, FALSE, v_fila.comision, v_fila.marca_agua_despues, v_fila.clave_pago, v_fila.movimiento_billetera_id;
            RETURN;
        END IF;
        SELECT MAX(r.periodo_hasta) INTO v_desde FROM comisiones_rendimiento r WHERE r.copia_id = p_copia;
        v_desde := COALESCE(v_desde, v_copia.creada_en);
        IF p_final THEN
            v_hasta := GREATEST(p_hasta, v_desde + INTERVAL '1 second');
        ELSIF p_hasta <= v_desde THEN
            RETURN;
        ELSE
            v_hasta := p_hasta;
        END IF;
        SELECT e.comision_pct INTO v_pct FROM estrategias e WHERE e.id = v_copia.estrategia_id;
        SELECT COALESCE(SUM(o.resultado), 0) INTO v_ganancia FROM operaciones o WHERE o.copia_id = p_copia AND o.resultado IS NOT NULL;
        v_marca := COALESCE(v_copia.marca_agua, 0);
        v_nueva_marca := ROUND(GREATEST(v_ganancia, v_marca), 2);
        v_comision := ROUND(GREATEST(0, v_ganancia - v_marca) * COALESCE(v_pct, 0) / 100, 2);
        v_clave := 'comision-' || p_copia::TEXT || '-' || to_char(v_hasta AT TIME ZONE 'UTC', 'YYYYMMDDHH24MISSUS');
        INSERT INTO comisiones_rendimiento (copia_id, periodo_desde, periodo_hasta, ganancia_acumulada, marca_agua_antes, marca_agua_despues, comision_pct, comision, clave_pago)
        VALUES (p_copia, v_desde, v_hasta, ROUND(v_ganancia, 2), v_marca, v_nueva_marca, COALESCE(v_pct, 0), v_comision, v_clave)
        RETURNING id INTO v_id;
        UPDATE copias SET marca_agua = v_nueva_marca WHERE id = p_copia;
        IF p_final THEN
            UPDATE copias SET comision_final_en = now() WHERE id = p_copia;
        END IF;
        RETURN QUERY SELECT v_id, TRUE, v_comision, v_nueva_marca, v_clave, NULL::BIGINT;
    END;
    $$;

-- -------------------------------------------
-- Función `billetera_recargar` --
-- -------------------------------------------

    -- Descripción: suma una recarga virtual a la billetera respetando el saldo máximo y el tope mensual de recargas, comprobados DESPUÉS de bloquear la fila de la billetera: dos recargas
    -- simultáneas se turnan y la segunda ve la primera. Falla con `saldo_maximo`, `tope_mensual` o `monto_invalido`. Con `p_clave` repetida no repite el movimiento.
    CREATE OR REPLACE FUNCTION billetera_recargar(p_usuario BIGINT, p_monto NUMERIC, p_saldo_max NUMERIC, p_tope_mensual NUMERIC, p_concepto TEXT DEFAULT '', p_clave TEXT DEFAULT NULL)
    RETURNS TABLE (saldo_nuevo NUMERIC, movimiento_id BIGINT, repetido BOOLEAN)
    LANGUAGE plpgsql AS $$
    DECLARE
        v_saldo NUMERIC;
        v_nuevo NUMERIC;
        v_mes NUMERIC;
        v_id BIGINT;
    BEGIN
        IF p_monto IS NULL OR p_monto <= 0 THEN
            RAISE EXCEPTION 'monto_invalido';
        END IF;
        INSERT INTO billetera_cuentas (usuario_id) VALUES (p_usuario) ON CONFLICT (usuario_id) DO NOTHING;
        SELECT c.saldo INTO v_saldo FROM billetera_cuentas c WHERE c.usuario_id = p_usuario FOR UPDATE;
        IF p_clave IS NOT NULL THEN
            SELECT m.id INTO v_id FROM billetera_movimientos m WHERE m.clave_unica = p_clave;
            IF FOUND THEN
                RETURN QUERY SELECT v_saldo, v_id, TRUE;
                RETURN;
            END IF;
        END IF;
        v_nuevo := v_saldo + p_monto;
        IF v_nuevo > p_saldo_max THEN
            RAISE EXCEPTION 'saldo_maximo';
        END IF;
        SELECT COALESCE(SUM(m.monto), 0) INTO v_mes FROM billetera_movimientos m
         WHERE m.usuario_id = p_usuario AND m.tipo = 'recarga_virtual' AND m.creado_en >= date_trunc('month', now() AT TIME ZONE 'UTC') AT TIME ZONE 'UTC';
        IF v_mes + p_monto > p_tope_mensual THEN
            RAISE EXCEPTION 'tope_mensual';
        END IF;
        UPDATE billetera_cuentas SET saldo = v_nuevo, actualizada_en = now() WHERE usuario_id = p_usuario;
        INSERT INTO billetera_movimientos (usuario_id, tipo, monto, saldo_despues, concepto, clave_unica)
        VALUES (p_usuario, 'recarga_virtual', p_monto, v_nuevo, COALESCE(p_concepto, ''), p_clave) RETURNING id INTO v_id;
        RETURN QUERY SELECT v_nuevo, v_id, FALSE;
    END;
    $$;

-- -------------------------------------------
-- Estructura de tabla para la tabla `billetera_compras` --
-- -------------------------------------------

    CREATE TABLE IF NOT EXISTS billetera_compras (

        -- Una fila por compra de plan con la billetera: guarda en qué paso va para poder retomarla si el proceso se interrumpe.
        id BIGSERIAL PRIMARY KEY,
        usuario_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
        plan TEXT NOT NULL,
        precio NUMERIC(14, 2) NOT NULL CHECK (precio > 0),
        -- iniciada: se reservó la compra y puede que aún no se cobre; cobrada: el dinero salió y falta activar el plan; activada: terminó bien;
        -- reembolsada: no se pudo activar y se devolvió el dinero; cancelada: nunca se cobró.
        estado TEXT NOT NULL DEFAULT 'iniciada' CHECK (estado IN ('iniciada', 'cobrada', 'activada', 'reembolsada', 'cancelada')),
        error TEXT,
        creada_en TIMESTAMPTZ NOT NULL DEFAULT now(),
        actualizada_en TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    -- Una sola compra en curso por usuario y plan (un doble clic no cobra dos veces).
    CREATE UNIQUE INDEX IF NOT EXISTS billetera_compras_en_curso ON billetera_compras (usuario_id, plan) WHERE estado IN ('iniciada', 'cobrada');
    CREATE INDEX IF NOT EXISTS billetera_compras_usuario ON billetera_compras (usuario_id, estado);

-- -------------------------------------------
-- Permisos --
-- -------------------------------------------

    -- El usuario de la base que usa la plataforma (hosting). Las funciones mueven dinero: solo la plataforma las ejecuta.
    GRANT SELECT, INSERT, UPDATE, DELETE ON billetera_compras TO vptzmybcspqcmxjgjakx;
    GRANT USAGE, SELECT ON SEQUENCE billetera_compras_id_seq TO vptzmybcspqcmxjgjakx;
    GRANT ALL ON comisiones_rendimiento TO vptzmybcspqcmxjgjakx;
    REVOKE ALL ON FUNCTION comision_liquidar(BIGINT, TIMESTAMPTZ, BOOLEAN) FROM PUBLIC;
    GRANT EXECUTE ON FUNCTION comision_liquidar(BIGINT, TIMESTAMPTZ, BOOLEAN) TO vptzmybcspqcmxjgjakx;
    REVOKE ALL ON FUNCTION billetera_recargar(BIGINT, NUMERIC, NUMERIC, NUMERIC, TEXT, TEXT) FROM PUBLIC;
    GRANT EXECUTE ON FUNCTION billetera_recargar(BIGINT, NUMERIC, NUMERIC, NUMERIC, TEXT, TEXT) TO vptzmybcspqcmxjgjakx;


-- -------------------------------------------------------------------------------------------------------
-- -------------------------- FIN Piña y Jara liquidaciones_y_billetera_atomicas .SQL --------------------
-- -------------------------------------------------------------------------------------------------------

-- Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
-- Dirección: José Joaquín Prieto #5373 -
-- San Miguel - Santiago - Chile
-- contacto.pinayjara@gmail.com
-- https://www.pinayjara.cl
-- Creado, Programado y Diseñado por Piña y Jara
-- Transportes y Servicios Ltda.
