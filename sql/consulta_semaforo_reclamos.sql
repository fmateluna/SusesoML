SELECT DISTINCT
    l.id_lic,
    l.rut_medico,
    l.fecha_emision,
    CASE
        WHEN ps.rn1 + ps.rn2 > 0 THEN 1
        ELSE 0
    END AS propensity_score_rn,
    u.score_frecuencia_medico_30d AS propensity_score_umbrales,
    ps.rn1,
    ps.rn2,
    a.propensity_score_iforest
FROM ml.licencias l
INNER JOIN ml.licencia_diagnostico_especialidad lde 
    ON l.id_lic = lde.id_licencia
LEFT JOIN LATERAL (
    SELECT
        MAX(score) FILTER (WHERE rn = 1) AS rn1,
        MAX(score) FILTER (WHERE rn = 2) AS rn2
    FROM ml.propensity_score ps
    WHERE ps.id_lic = l.id_lic
) ps ON true
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