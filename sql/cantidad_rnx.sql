-- SQLBook: Code
SELECT
    TO_CHAR(l.fecha_emision, 'DD-MM-YYYY') AS fecha,
    COUNT(*)
FROM
    licencias l,
    licencia_diagnostico_especialidad lde,
    propensity_score sc
WHERE
    l.id_lic = lde.id_licencia and
    l.fecha_emision  BETWEEN :fecha_inicio AND :fecha_fin 
    and sc.id_lic = l.id_lic 
GROUP BY
    TO_CHAR(l.fecha_emision, 'DD-MM-YYYY')
ORDER BY
    TO_DATE(TO_CHAR(l.fecha_emision, 'DD-MM-YYYY'), 'DD-MM-YYYY');