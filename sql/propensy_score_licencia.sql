-- SQLBook: Code
SELECT 
	l.id_lic ,
    l.fecha_emision ,
    l.rut_medico ,
    l.dias_reposo ,
    lde.cod_diagnostico,
    lde.especialidad_medico,
    ps.rn,
    ps.score
FROM 
    ml.licencias l
    INNER JOIN ml.licencia_diagnostico_especialidad lde ON l.id_lic = lde.id_licencia
    INNER JOIN ml.propensity_score ps ON l.id_lic = ps.id_lic
WHERE 
	1=1
    and l.fecha_emision BETWEEN :fecha_inicio AND :fecha_fin 