SELECT
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
    created_at
FROM ml.semaforo
WHERE (:rut_medico IS NULL OR rut_medico = :rut_medico)
  AND (:rango IS NULL OR rango = :rango);