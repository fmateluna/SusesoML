SELECT
    fui_uclm AS "FUI_UCLM",
    expediente_uclm AS "EXPEDIENTE_UCLM",
    num_licencia AS "NUM_LICENCIA",
    rut_afectado AS "RUT_AFECTADO",
    dv_afectado AS "DV_AFECTADO",
    apellido_paterno_afectado AS "APELLIDO_PATERNO_AFECTADO",
    apellido_materno_afectado AS "APELLIDO_MATERNO_AFECTADO",
    nombres_afectado AS "NOMBRES_AFECTADO",
    sexo_afectado AS "SEXO_AFECTADO",
    razon_social AS "RAZON_SOCIAL",
    prevision_salud_afectado AS "PREVISION_SALUD_AFECTADO",
    patologia_licencia_afectado AS "PATOLOGIA_LICENCIA_AFECTADO",
    patologia_simplificada AS "PATOLOGIA_SIMPLIFICADA",
    rut_empleador_afectado AS "RUT_EMPLEADOR_AFECTADO",
    codigo_compin_art2 AS "CODIGO_COMPIN_ART2",
    compin_art2 AS "COMPIN_ART2",
    resol_art2 AS "RESOL_ART2",
    fecha_emision_art2 AS "FECHA_EMISION_ART2",
    dias_suspension_art2 AS "DIAS_SUSPENSION_ART2",
    monto_multa_art2 AS "MONTO_MULTA_ART2"
FROM pae_sabana.uclmdetalle
WHERE EXTRACT(YEAR FROM fecha_emision_art2) = :anio
  AND EXTRACT(MONTH FROM fecha_emision_art2) = :mes;