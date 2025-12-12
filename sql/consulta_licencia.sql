SELECT
    l.id_lic,
    l.operador,
    l.ccaf,
    l.entidad_pagadora,
    l.folio,
    l.fecha_emision,
    l.empleador_adscrito,
    l.codigo_interno_prestador,
    l.comuna_prestador,
    l.fecha_ultimo_estado,
    l.ultimo_estado,
    l.rut_trabajador,
    l.sexo_trabajador,
    l.edad_trabajador,
    l.tipo_reposo,
    l.dias_reposo,
    l.fecha_inicio_reposo,
    l.comuna_reposo,
    l.tipo_licencia,
    l.rut_medico,
    l.tipo_licencia_pronunciamiento,
    l.codigo_continuacion_pronunciamiento,
    l.dias_autorizados_pronunciamiento,
    l.codigo_diagnostico_pronunciamiento,
    l.codigo_autorizacion_pronunciamiento,
    l.causa_rechazo_pronunciamiento,
    l.tipo_reposo_pronunciamiento,
    l.derecho_a_subsidio_pronunciamiento,
    l.rut_empleador,
    l.calidad_trabajador,
    l.actividad_laboral_trabajador,
    l.ocupacion,
    l.entidad_pagadora_zona_c,
    l.fecha_recepcion_empleador,
    l.regimen_previsional,
    l.entidad_pagadora_subsidio,
    l.comuna_laboral,
    l.comuna_uso_compin,
    l.cantidad_de_pronunciamientos,
    l.cantidad_de_zonas_d,
    l.secuencia_estados,
    l.cod_diagnostico_principal,
    l.cod_diagnostico_secundario,
    l.periodo,
    l.marca_otorgamiento,
    lde.cod_diagnostico,
    lde.especialidad_medico,
    ps.rn1,
    ps.rn2,
    u.score_frecuencia_medico_7d,
    u.score_frecuencia_medico_15d,
    u.score_frecuencia_medico_30d,
    u.score_frecuencia_f_30d_medico,
    u.score_frecuencia_j_30d_medico,
    u.score_frecuencia_m_30d_medico,
    u.score_n_remotas_30d,
    u.score_n_presenciales_30d,
    a.id AS anomalias_id,
    a.hora_emision AS anomalias_hora_emision,
    a.dia_codificado AS anomalias_dia_codificado,
    a.calidad_trabajador_independiente AS anomalias_calidad_trabajador_independiente,
    a.calidad_trabajador_dependiente_privado AS anomalias_calidad_trabajador_dependiente_privado,
    a.calidad_trabajador_publico_afecto AS anomalias_calidad_trabajador_publico_afecto,
    a.calidad_trabajador_publico_no_afecto AS anomalias_calidad_trabajador_publico_no_afecto,
    a.recencia_trabajador AS anomalias_recencia_trabajador,
    a.frecuencia_trabajador_60d AS anomalias_frecuencia_trabajador_60d,
    a.frecuencia_trabajador_40d AS anomalias_frecuencia_trabajador_40d,
    a.frecuencia_trabajador_20d AS anomalias_frecuencia_trabajador_20d,
    a.reposo_trabajador_60d AS anomalias_reposo_trabajador_60d,
    a.reposo_trabajador_40d AS anomalias_reposo_trabajador_40d,
    a.reposo_trabajador_20d AS anomalias_reposo_trabajador_20d,
    a.n_medicos_distintos_xtrabajador_60d AS anomalias_n_medicos_distintos_xtrabajador_60d,
    a.n_empleadores_distintos_xtrabajador_60d AS anomalias_n_empleadores_distintos_xtrabajador_60d,
    a.desviacion_reposo_trabajador_60d AS anomalias_desviacion_reposo_trabajador_60d,
    a.recencia_medico AS anomalias_recencia_medico,
    a.reposo_medico_30d AS anomalias_reposo_medico_30d,
    a.reposo_medico_15d AS anomalias_reposo_medico_15d,
    a.reposo_medico_7d AS anomalias_reposo_medico_7d,
    a.licencias_20_min AS anomalias_licencias_20_min,
    a.licencias_40_min AS anomalias_licencias_40_min,
    a.licencias_60_min AS anomalias_licencias_60_min,
    a.max_licencias_dia_30d AS anomalias_max_licencias_dia_30d,
    a.max_rest_days_30d AS anomalias_max_rest_days_30d,
    a.diferencia_dias AS anomalias_diferencia_dias,
    a.licencias_despues_umbral AS anomalias_licencias_despues_umbral,
    a.n_trabajadores_distintos_xmedico_60d AS anomalias_n_trabajadores_distintos_xmedico_60d,
    a.n_empleadores_distintos_xmedico_60d AS anomalias_n_empleadores_distintos_xmedico_60d,
    a.hhi_empleadores_por_medico_60d AS anomalias_hhi_empleadores_por_medico_60d,
    a.recencia_empleador AS anomalias_recencia_empleador,
    a.frecuencia_empleador_60d AS anomalias_frecuencia_empleador_60d,
    a.frecuencia_empleador_40d AS anomalias_frecuencia_empleador_40d,
    a.frecuencia_empleador_20d AS anomalias_frecuencia_empleador_20d,
    a.reposo_empleador_60d AS anomalias_reposo_empleador_60d,
    a.reposo_empleador_40d AS anomalias_reposo_empleador_40d,
    a.reposo_empleador_20d AS anomalias_reposo_empleador_20d,
    a.n_trabajadores_distintos_xempleador_60d AS anomalias_n_trabajadores_distintos_xempleador_60d,
    a.n_medicos_distintos_xempleador_60d AS anomalias_n_medicos_distintos_xempleador_60d,
    a.frecuencia_j_30d_empleador AS anomalias_frecuencia_j_30d_empleador,
    a.frecuencia_f_30d_empleador AS anomalias_frecuencia_f_30d_empleador,
    a.frecuencia_m_30d_empleador AS anomalias_frecuencia_m_30d_empleador,
    a.historial_trabajador_medico AS anomalias_historial_trabajador_medico,
    a.historial_empleador_medico AS anomalias_historial_empleador_medico,
    a.ponderado_medico_trabajador AS anomalias_ponderado_medico_trabajador,
    a.anomaly_score AS anomalias_anomaly_score,
    a.propensity_score_iforest AS anomalias_propensity_score_iforest,
    a.fecha_creacion AS anomalias_fecha_creacion
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
LEFT JOIN ml.umbrales u
    ON l.id_lic = u.id_lic
LEFT JOIN ml.anomalias a
    ON l.id_lic = a.id_lic
WHERE
    (:id_lic IS NULL OR l.id_lic = :id_lic)
    AND (:rut_trabajador IS NULL OR l.rut_trabajador = :rut_trabajador)
    AND (:rut_medico IS NULL OR l.rut_medico = :rut_medico)
    AND (:rut_empleador IS NULL OR l.rut_empleador = :rut_empleador)
    AND (:folio IS NULL OR l.folio = :folio)
    AND (:cod_diagnostico IS NULL OR lde.cod_diagnostico = :cod_diagnostico)
    AND (:especialidad_medico IS NULL OR lde.especialidad_medico = :especialidad_medico)
    AND (
        (:fecha_unica IS NOT NULL AND l.fecha_emision = :fecha_unica)
        OR (
            :fecha_unica IS NULL
            AND :fecha_inicio IS NOT NULL
            AND :fecha_fin IS NOT NULL
            AND l.fecha_emision BETWEEN :fecha_inicio AND :fecha_fin
        )
    )
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
