-- SQLBook: Code
SELECT 
    lic.id_lic AS id_licencia,
    lic.folio,
    lic.dias_reposo,
    lic.fecha_emision,
    lic.fecha_inicio_reposo,
    diag.especialidad_medico AS especialidad_profesional,
    diag.cod_diagnostico AS cod_diagnostico_principal
FROM ml.licencias lic
INNER JOIN ml.licencia_diagnostico_especialidad diag
    ON lic.id_lic = diag.id_licencia
WHERE lic.fecha_emision BETWEEN :fecha_inicio AND :fecha_fin;