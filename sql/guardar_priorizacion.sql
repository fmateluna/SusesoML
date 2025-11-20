-- sql/guardar_priorizacion.sql
INSERT INTO ml.priorizacion (denuncia_id, valor_priorizacion, fecha_actualizacion, fecha_creacion, rut_medico, fecha_ingreso, sancionado, no_admisible, decision)
VALUES (:denuncia_id, :valor_priorizacion, :fecha_actualizacion, :fecha_creacion, :rut_medico, :fecha_ingreso, :sancionado, :no_admisible, :decision)
ON CONFLICT (denuncia_id) DO UPDATE SET
    valor_priorizacion = EXCLUDED.valor_priorizacion,
    fecha_actualizacion = EXCLUDED.fecha_actualizacion,
    rut_medico = EXCLUDED.rut_medico,
    fecha_ingreso = EXCLUDED.fecha_ingreso,
    sancionado = EXCLUDED.sancionado,
    no_admisible = EXCLUDED.no_admisible,
    decision = EXCLUDED.decision;
