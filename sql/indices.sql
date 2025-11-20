-- Índices para la tabla ml.licencias
CREATE INDEX IF NOT EXISTS idx_licencias_id_lic ON ml.licencias (id_lic);
CREATE INDEX IF NOT EXISTS idx_licencias_rut_emisor ON ml.licencias (rut_emisor);
CREATE INDEX IF NOT EXISTS idx_licencias_anio_mes ON ml.licencias (anio_licencia, mes_licencia);
CREATE INDEX IF NOT EXISTS idx_licencias_fecha_emision ON ml.licencias (fecha_emision);

-- Índices para la tabla ml.propensity_score
CREATE INDEX IF NOT EXISTS idx_propensity_id_lic ON ml.propensity_score (id_lic);

-- Índices para la tabla ml.licencia_diagnostico_especialidad
CREATE INDEX IF NOT EXISTS idx_lic_diag_esp_id_licencia ON ml.licencia_diagnostico_especialidad (id_licencia);

-- Índices para la tabla ml.umbrales
CREATE INDEX IF NOT EXISTS idx_umbrales_rut_medico ON ml.umbrales (rut_medico);
