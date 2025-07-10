-- SQLBook: Code
SELECT 
    l.fecha_emision::date AS fecha_emision,
    ps.rn,
    COUNT(*) AS cantidad_registros
FROM 
    ml.licencias l
    INNER JOIN ml.licencia_diagnostico_especialidad lde ON l.id_lic = lde.id_licencia
    INNER JOIN ml.propensity_score ps ON l.id_lic = ps.id_lic
WHERE 
    l.fecha_emision BETWEEN :fecha_inicio AND :fecha_fin
GROUP BY 
    ps.rn,
    l.fecha_emision::date
ORDER BY 
    l.fecha_emision::date, ps.rn

/*
SELECT 
    lde.cod_diagnostico,
    lde.especialidad_medico,
    ps.rn,
    COUNT(*) as cantidad_registros
FROM 
    ml.licencias l
    INNER JOIN ml.licencia_diagnostico_especialidad lde ON l.id_lic = lde.id_licencia
    INNER JOIN ml.propensity_score ps ON l.id_lic = ps.id_lic
WHERE 
    l.fecha_emision BETWEEN :fecha_inicio AND :fecha_fin  -- Replace with your desired date range
GROUP BY 
    lde.cod_diagnostico,
    lde.especialidad_medico,
    ps.rn
*/