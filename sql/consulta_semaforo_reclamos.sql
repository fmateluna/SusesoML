SELECT
    l.id_lic,
    l.rut_medico,
    l.fecha_emision,
    ps.rn1 AS propensity_score_rn,
    u.score_frecuencia_medico_30d AS propensity_score_umbrales,
    a.propensity_score_iforest
FROM ml.licencias l
INNER JOIN ml.licencia_diagnostico_especialidad lde 
    ON l.id_lic = lde.id_licencia
LEFT JOIN LATERAL (
    SELECT
        MAX(score) FILTER (WHERE rn = 1) AS rn1
    FROM ml.propensity_score ps
    WHERE ps.id_lic = l.id_lic
) ps ON true
LEFT JOIN ml.umbrales u
    ON l.id_lic = u.id_lic
LEFT JOIN ml.anomalias a
    ON l.id_lic = a.id_lic
WHERE
    EXTRACT(YEAR FROM l.fecha_emision) = :anio
    AND EXTRACT(MONTH FROM l.fecha_emision) = :mes
    AND (:rut_medico IS NULL OR l.rut_medico = :rut_medico)
    AND u.score_frecuencia_medico_7d IS NOT NULL
    AND u.score_frecuencia_medico_15d IS NOT NULL
    AND u.score_frecuencia_medico_30d IS NOT NULL
    AND u.score_frecuencia_f_30d_medico IS NOT NULL
    AND u.score_frecuencia_j_30d_medico IS NOT NULL
    AND u.score_frecuencia_m_30d_medico IS NOT NULL
    AND u.score_n_remotas_30d IS NOT NULL
    AND u.score_n_presenciales_30d IS NOT NULL
    AND a.anomaly_score IS NOT NULL
    AND a.propensity_score_iforest IS NOT NULL;