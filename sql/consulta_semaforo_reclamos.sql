SELECT DISTINCT
    l.id_lic,
    l.rut_medico,
    l.fecha_emision,
    ps.score AS propensity_score_rn,
    u.score_frecuencia_medico_30d AS propensity_score_umbrales,
    a.propensity_score_iforest
FROM ml.licencias l
INNER JOIN ml.licencia_diagnostico_especialidad lde 
    ON l.id_lic = lde.id_licencia
LEFT JOIN ml.propensity_score ps
    ON l.id_lic = ps.id_lic AND ps.rn = 1
INNER JOIN ml.umbrales u
    ON l.id_lic = u.id_lic 
    AND u.score_frecuencia_medico_30d IS NOT NULL 
INNER JOIN ml.anomalias a
    ON l.id_lic = a.id_lic 
    AND a.propensity_score_iforest IS NOT NULL  
WHERE
    l.fecha_emision >= DATE_TRUNC('month', MAKE_DATE(:anio, :mes, 1))
    AND l.fecha_emision < DATE_TRUNC('month', MAKE_DATE(:anio, :mes, 1)) + INTERVAL '1 month'
    AND (:rut_medico IS NULL OR l.rut_medico = :rut_medico);