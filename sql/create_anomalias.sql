CREATE SCHEMA IF NOT EXISTS ml;

DROP TABLE IF EXISTS ml.anomalias;

CREATE TABLE ml.anomalias (
    id SERIAL PRIMARY KEY,
    rut_medico VARCHAR(15),
    rut_trabajador VARCHAR(15),
    rut_empleador VARCHAR(15),
    fecha_emision TIMESTAMP NOT NULL,
    dias_reposo INT,
    cod_diagnostico_principal VARCHAR(10),
    marca_otorgamiento VARCHAR(20),

    -- Conteos por otorgamiento
    n_remotas_30D INT,
    n_presenciales_30D INT,

    -- Conteos por entidad
    licencias_7D INT,
    licencias_15D INT,
    licencias_30D INT,

    -- Reposo acumulado
    dias_reposo_30D INT,
    desviacion_reposo_30D NUMERIC(10,4),

    -- Diagnósticos frecuentes (ejemplo: letras A, B, C, D…)
    frecuencia_A_30D_medico INT,
    frecuencia_B_30D_medico INT,
    frecuencia_C_30D_medico INT,
    frecuencia_D_30D_medico INT,
    -- puedes agregar más columnas dinámicas según las letras que uses

    -- Máximos por periodo
    max_licencias_30D INT,
    max_reposo_30D INT,

    -- Indicadores de umbral
    diferencia_dias INT,
    licencias_despues_umbral INT,

    -- Concentración de empleadores
    hhi_empleadores NUMERIC(10,4),

    -- Ventanas en minutos
    licencias_20_min INT,
    licencias_40_min INT,
    licencias_60_min INT,

    -- Conteos por empleador
    licencias_empleador_30D INT,
    dias_reposo_empleador_30D INT,

    created_at TIMESTAMP DEFAULT NOW()
);

-- Índice primario si id_lic es único
ALTER TABLE ml.anomalias
ADD CONSTRAINT anomalias_pk PRIMARY KEY (id_lic);

-- Índice para búsquedas por fecha
CREATE INDEX idx_anomalias_fecha_emision
ON ml.anomalias (fecha_emision);

-- Índice combinado para consultas por id_lic + fecha
CREATE INDEX idx_anomalias_id_fecha
ON ml.anomalias (id_lic, fecha_emision);

-- Si haces muchas consultas por rango de fechas, un BRIN puede ser mejor
CREATE INDEX idx_anomalias_fecha_brin
ON ml.anomalias USING BRIN (fecha_emision);
