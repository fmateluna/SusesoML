CREATE TABLE IF NOT EXISTS ml.reclamos_data (
    hash TEXT PRIMARY KEY,
    anio INTEGER,
    mes INTEGER,
    rut_medico TEXT,
    estado TEXT,
    created_at TIMESTAMP
);
