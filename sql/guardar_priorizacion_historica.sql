-- Este script inserta un nuevo registro en ml.priorizacion_historica solo si los valores
-- de los campos clave (valor_priorizacion, sancionado, no_admisible, decision)
-- difieren de los del último registro existente para la misma denuncia_id.
-- Se utiliza 'IS NOT DISTINCT FROM' para una comparación segura que maneja NULLs correctamente.
INSERT INTO ml.priorizacion_historica (
    denuncia_id, valor_priorizacion, fecha_actualizacion, fecha_creacion,
    rut_medico, fecha_ingreso, sancionado, no_admisible, decision
)
SELECT
    :denuncia_id, :valor_priorizacion, :fecha_actualizacion, :fecha_creacion,
    :rut_medico, :fecha_ingreso, :sancionado, :no_admisible, :decision
WHERE
    NOT EXISTS (
        SELECT 1 FROM (
            -- Primero, obtenemos el registro más reciente para esta denuncia
            SELECT
                valor_priorizacion,
                sancionado,
                no_admisible,
                decision
            FROM ml.priorizacion_historica
            WHERE denuncia_id = :denuncia_id
            ORDER BY fecha_creacion DESC
            LIMIT 1
        ) AS ultimo_registro
        -- Ahora, comparamos si los datos del registro más reciente son iguales a los nuevos datos
        WHERE
            ultimo_registro.valor_priorizacion IS NOT DISTINCT FROM :valor_priorizacion
            AND ultimo_registro.sancionado IS NOT DISTINCT FROM :sancionado
            AND ultimo_registro.no_admisible IS NOT DISTINCT FROM :no_admisible
            AND ultimo_registro.decision IS NOT DISTINCT FROM :decision
    );
