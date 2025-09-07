SELECT 
    l.id_lic AS id_licencia,
    l.folio,
    l.dias_reposo,
    l.fecha_emision,
    l.fecha_inicio_reposo,
    lde.especialidad_medico AS especialidad_profesional,
    l.cod_diagnostico_principal,
    l.rut_medico,
    l.rut_trabajador,
    l.calidad_trabajador,
    l.rut_empleador,
    l.marca_otorgamiento,
    l.edad_trabajador,
    l.sexo_trabajador,
    COALESCE(e.num_trabajadores, 0) AS n_trabajadores
FROM ml.licencias l
INNER JOIN ml.licencia_diagnostico_especialidad lde 
    ON lde.id_licencia = l.id_lic
LEFT JOIN ml.empresa e 
    ON e.rut_empresa = l.rut_empleador
WHERE 
    l.fecha_emision BETWEEN 
        DATE_TRUNC('day', CAST(:fecha_inicio AS TIMESTAMP)) - INTERVAL ':windows_days days' 
        AND DATE_TRUNC('day', CAST(:fecha_inicio AS TIMESTAMP)) + INTERVAL '1 day' - INTERVAL '1 second'