import logging

from core.utils.license_processing import count_licenses_by_entity, count_licenses_by_otorgamiento, count_licenses_by_diagnosis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_umbral_data(df, entity_col='rut_medico',dias=60):
    """
    Procesa el DataFrame aplicando filtros y calculando métricas de umbral.

    Parámetros:
        df (pd.DataFrame): DataFrame con datos de licencias.
        entity_col (str): Columna de entidad (por ejemplo, 'rut_medico').        

    Retorna:
        pd.DataFrame: DataFrame procesado con columnas adicionales.
    """
    try:
        # Aplicar filtros iniciales
        df = df[df['dias_reposo'] <= 365]
        df = df[~df['cod_diagnostico_principal'].isin(['U07.1', 'U07.2'])]
        df['fecha_emision'] = pd.to_datetime(df['fecha_emision'], errors='coerce')
        df = df.sort_values(by=[entity_col, 'rut_trabajador', 'fecha_emision']).reset_index(drop=True)

        # Calcular frecuencias por entidad
        df['frecuencia_medico_30D'] = count_licenses_by_entity(df, entity_col=entity_col, window_days=30)
        df['frecuencia_medico_15D'] = count_licenses_by_entity(df, entity_col=entity_col, window_days=15)
        df['frecuencia_medico_7D'] = count_licenses_by_entity(df, entity_col=entity_col, window_days=7)

        # Los windows_days de cada columnas son fijos
        df = count_licenses_by_diagnosis(df, window_days=30, cods_list=['J', 'F', 'M'], entity_col=entity_col)

        # Calcular licencias remotas y presenciales
        df = count_licenses_by_otorgamiento(df, entity_col=entity_col, window_days=30)
        
        return df

    except Exception as e:
        logger.error(f"Error procesando datos de umbral: {str(e)}")
        raise


