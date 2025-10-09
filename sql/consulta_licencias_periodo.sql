SELECT 
    dias_reposo,
    cod_diagnostico_principal,
    fecha_emision,
    fecha_recepcion_empleador,
    rut_medico,
    id_lic
FROM ml.licencias l
WHERE TO_CHAR(l.fecha_emision, 'YYYY') = :anio
  AND TO_CHAR(l.fecha_emision, 'MM') = :mes;
