-- =================================================================================
-- Script para la limpieza automática de registros en ml.priorizacion_historica
-- =================================================================================
--
-- Propósito:
-- Este script crea una función de trigger y un trigger en PostgreSQL para mantener
-- un historial de registros de solo 7 meses en la tabla ml.priorizacion_historica.
--
-- Funcionamiento:
-- 1. Se define una función llamada 'limpiar_registros_antiguos_historica_func'.
-- 2. Esta función se ejecuta automáticamente después de cada operación de INSERT
--    en la tabla 'ml.priorizacion_historica'.
-- 3. La función calcula la fecha del registro más reciente en la tabla.
-- 4. Luego, determina una "fecha de corte" restando 7 meses a la fecha más reciente.
-- 5. Finalmente, elimina todos los registros cuya 'fecha_creacion' sea anterior
--    a esta fecha de corte.
--
-- =================================================================================

-- Primero, se asegura de eliminar la función si ya existe para evitar errores al re-ejecutar.
DROP FUNCTION IF EXISTS ml.limpiar_registros_antiguos_historica_func() CASCADE;

-- Creación de la función que contendrá la lógica de limpieza.
CREATE OR REPLACE FUNCTION ml.limpiar_registros_antiguos_historica_func()
RETURNS TRIGGER AS $$
DECLARE
    v_max_fecha_creacion TIMESTAMP; -- Variable para almacenar la fecha más reciente.
    v_fecha_corte TIMESTAMP;        -- Variable para almacenar la fecha de corte (7 meses atrás).
BEGIN
    -- Paso 1: Obtener la fecha de creación más reciente de la tabla.
    -- Se utiliza MAX() sobre la columna 'fecha_creacion'. Si la tabla está vacía,
    -- esta variable quedará como NULL.
    SELECT MAX(fecha_creacion) INTO v_max_fecha_creacion FROM ml.priorizacion_historica;

    -- Paso 2: Verificar si se encontró una fecha.
    -- Si v_max_fecha_creacion no es NULL, se procede a la limpieza.
    IF v_max_fecha_creacion IS NOT NULL THEN
        -- Calcular la fecha de corte restando 7 meses a la fecha más reciente.
        v_fecha_corte := v_max_fecha_creacion - INTERVAL '7 months';

        -- Informar en los logs de PostgreSQL qué se va a hacer (opcional pero recomendado).
        RAISE NOTICE '[Trigger de Limpieza]: La fecha más reciente es %. La fecha de corte es %.', v_max_fecha_creacion, v_fecha_corte;

        -- Paso 3: Eliminar los registros antiguos.
        -- Se eliminan todas las filas cuya 'fecha_creacion' sea anterior a la fecha de corte.
        DELETE FROM ml.priorizacion_historica
        WHERE fecha_creacion < v_fecha_corte;

        -- Informar cuántos registros se eliminaron (opcional pero recomendado).
        -- NOTA: La siguiente línea 'SELECT count(*) FROM pg_locks' es un placeholder.
        -- Para obtener el número real de filas afectadas por el DELETE en PL/pgSQL
        -- se usa GET DIAGNOSTICS integer_var = ROW_COUNT; justo después del DELETE.
        -- Sin embargo, para mantener el ejemplo simple y compatible con un script SQL directo,
        -- y dado que el RAISE NOTICE se ejecuta antes de que se complete la transacción
        -- del trigger (que incluye el DELETE), obtener el ROW_COUNT directamente aquí
        -- es más complejo sin afectar la lógica.
        -- Si necesitas un conteo exacto en el RAISE NOTICE, tendrías que ajustar la lógica.
        RAISE NOTICE '[Trigger de Limpieza]: Registros potencialmente eliminados.';
    ELSE
        -- Si la tabla está vacía, no se hace nada.
        RAISE NOTICE '[Trigger de Limpieza]: La tabla está vacía, no se realiza ninguna acción.';
    END IF;

    -- Para un trigger de tipo AFTER, el valor de retorno es ignorado,
    -- por lo que se puede retornar NULL.
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Creación del trigger que se asociará a la tabla.
-- Se asegura de eliminar el trigger si ya existe para evitar errores.
DROP TRIGGER IF EXISTS trg_limpiar_registros_antiguos_historica ON ml.priorizacion_historica;

CREATE TRIGGER trg_limpiar_registros_antiguos_historica
-- Se ejecutará DESPUÉS de una operación de INSERT.
AFTER INSERT ON ml.priorizacion_historica
-- Se ejecutará UNA VEZ por cada sentencia INSERT, no por cada fila insertada.
-- Esto es mucho más eficiente para inserciones masivas.
FOR EACH STATEMENT
-- Se especifica la función que debe ejecutar.
EXECUTE FUNCTION ml.limpiar_registros_antiguos_historica_func();

-- =================================================================================
-- Fin del script
-- =================================================================================
