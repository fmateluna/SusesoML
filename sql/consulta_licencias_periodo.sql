SELECT 
    dias_reposo,
    cod_diagnostico_principal,
    fecha_emision,
    fecha_recepcion_empleador,
    rut_medico,
    id_lic
FROM ml.licencias l
WHERE l.fecha_emision >= (:anio || '-' || :mes || '-01')::date
  AND l.fecha_emision < ((:anio || '-' || :mes || '-01')::date + INTERVAL '1 month');
