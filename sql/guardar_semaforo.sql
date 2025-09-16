INSERT INTO ml.semaforo (
    rut_medico,
    n_lic,
    rn,
    rango,
    um,
    an,
    smf_rn,
    smf_um,
    smf_an,
    created_at
) VALUES (
    :rut_medico,
    :n_lic,
    :rn,
    :rango,
    :um,
    :an,
    :smf_rn,
    :smf_um,
    :smf_an,
    :created_at
)
ON CONFLICT (rut_medico, rango) DO UPDATE
SET n_lic   = EXCLUDED.n_lic,
    rn      = EXCLUDED.rn,
    um      = EXCLUDED.um,
    an      = EXCLUDED.an,
    smf_rn  = EXCLUDED.smf_rn,
    smf_um  = EXCLUDED.smf_um,
    smf_an  = EXCLUDED.smf_an,
    created_at = EXCLUDED.created_at
RETURNING
    id,
    rut_medico,
    n_lic,
    rn,
    rango,
    um,
    an,
    smf_rn,
    smf_um,
    smf_an,
    created_at;
