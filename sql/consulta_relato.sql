SELECT
    folio_fui AS "FUN_FOLIO",
    folio_expediente ,
    flujo ,
    relato AS "FUN_RELATO",
    archivo ,
    ruta ,
    num_linea 
FROM pae_sabana.relato
WHERE
    EXTRACT(YEAR FROM fecha_ingreso) = :anio
    AND EXTRACT(MONTH FROM fecha_ingreso) = :mes;
