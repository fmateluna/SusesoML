

SELECT
    li.id_lic,
    li.folio,
    li.dias_reposo,
    li.fecha_emision,
    li.calidad_trabajador,
    li.fecha_inicio_reposo,
    ep.descripcion_especialidad_profesional,
    li.cod_diagnostico_principal
FROM
    ml.licencias AS li
    JOIN ml.especialidad_profesional_medicos epm 
        ON li.rut_medico = epm.rut_medico
    JOIN ml.especialidad_profesional ep 
        ON epm.id_especialidad_profesional = ep.id_especialidad_profesional
WHERE
    li.fecha_emision BETWEEN :fecha_inicio AND :fecha_fin
    AND (
        :cod_diagnostico_principal IS NULL 
        OR li.cod_diagnostico_principal = :cod_diagnostico_principal
    )
    AND (
        :especialidad_profesional IS NULL
        OR ep.descripcion_especialidad_profesional ILIKE '%' || :especialidad_profesional || '%'
    )
    AND NOT EXISTS (
        SELECT 1
        FROM ml.propensity_score ps
        WHERE ps.id_lic = li.id_lic
        AND ps.rn = 1
    );
