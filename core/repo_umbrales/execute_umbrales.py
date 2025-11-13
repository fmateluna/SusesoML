import sys
import pandas as pd
import numpy as np
import logging
import pickle as pkl
import os

from core.services import insert_umbrales
# from core.utils.custom_umbrales_logger import get_custom_umbrales_logger

# Configura el umbrales_logger personalizado para umbrales
# umbrales_umbrales_logger = get_custom_umbrales_logger('umbrales_umbrales_logger', 'umbrales.log')
umbrales_umbrales_logger = logging.getLogger('umbrales_umbrales_logger')

class Umbrales:
    def __init__(self, col_frecuencia):
        self.col_frecuencia = col_frecuencia
        self.umbral_min = None
        self.umbral_max = None

    def fit(self, df):
        valores = df[self.col_frecuencia].dropna()
        self.umbral_min = valores.mean() + 2 * valores.std()
        self.umbral_max = valores.mean() + 3 * valores.std()

    def predict_proba(self, df):
        if self.umbral_min is None or self.umbral_max is None:
            raise ValueError("Debes ejecutar fit() antes de predecir.")
        
        def calcular_score(x):
            if pd.isna(x):
                return np.nan
            elif x < self.umbral_min:
                return 0
            elif x > self.umbral_max:
                return 1
            else:
                return (x - self.umbral_min) / (self.umbral_max - self.umbral_min)

        return df[self.col_frecuencia].apply(calcular_score)

# Configure logging
logging.basicConfig(level=logging.INFO)
umbrales_logger = logging.getLogger(__name__)

_model_cache = {}


def get_model(model_path):
    """Obtiene el modelo desde cache o lo carga si no existe."""
    if model_path not in _model_cache:
        umbrales_logger.info(f"Cargando modelo desde disco: {model_path}")
        with open(model_path, 'rb') as f:
            _model_cache[model_path] = pkl.load(f)
    return _model_cache[model_path]


def preload_models(base_path):
    """Precarga todos los modelos en memoria al inicio."""
    models = [
        'umbral_model_frecuencia_medico_7D.pkl',
        'umbral_model_frecuencia_medico_15D.pkl',
        'umbral_model_frecuencia_medico_30D.pkl',
        'umbral_model_frecuencia_F_30D_medico.pkl',
        'umbral_model_frecuencia_J_30D_medico.pkl',
        'umbral_model_frecuencia_M_30D_medico.pkl',
        'umbral_model_n_remotas_30D.pkl',
        'umbral_model_n_presenciales_30D.pkl'
    ]
    for m in models:
        path = os.path.join(base_path, m)
        get_model(path)  # carga y mete a _model_cache
    umbrales_logger.info("Todos los modelos precargados en memoria.")


def apply_model(df, config):
    """Función para aplicar un modelo usando cache."""
    model_path = config['path']
    try:
        model = get_model(model_path)  # Usa cache en lugar de disco
        umbrales_logger.info(f"Ejecutando MODELO {model_path}")

        if hasattr(model, 'window_days') and model.window_days != config['days']:
            umbrales_umbrales_logger.warning(f"El modelo en {model_path} tiene window_days={model.window_days}, esperado {config['days']}.")

        # Fit y predict_proba, agregando la columna de score
        model.fit(df)
        if hasattr(model, 'col_frecuencia'):
            filename = os.path.basename(model_path) 
            base_name = filename.replace("umbral_model_", "").replace(".pkl", "")
            score_col = f"score_{base_name}"
            df[score_col] = model.predict_proba(df)
            umbrales_logger.info(f"Modelo {model_path} aplicado. Columna agregada: {score_col}")
        else:
            umbrales_logger.warning(f"El modelo en {model_path} no tiene 'col_frecuencia'.")
        return df
    except Exception as e:
        umbrales_logger.error(f"Error al aplicar modelo {model_path}: {str(e)}")
        return df
    

def process_umbral_data(df, entity_col='rut_medico', base_path=None):
    try:
        if base_path is None:
            # Obtener el directorio del archivo Python actual de manera dinámica
            base_path = os.path.dirname(os.path.abspath(__file__)) + '/'        

        # Precargar todos los modelos una sola vez
        if not _model_cache:  
            preload_models(base_path)

        # Aplicar filtros iniciales
        df = df[df['dias_reposo'] <= 365]
        df = df[~df['cod_diagnostico_principal'].isin(['U07.1', 'U07.2'])]
        df['fecha_emision'] = pd.to_datetime(df['fecha_emision'], errors='coerce')
        df = df.sort_values(by=[entity_col, 'rut_trabajador', 'fecha_emision']).reset_index(drop=True)

        # Lista de modelos con config
        models_config = [
            {'path': base_path + 'umbral_model_frecuencia_medico_7D.pkl', 'days': 7},
            {'path': base_path + 'umbral_model_frecuencia_medico_15D.pkl', 'days': 15},
            {'path': base_path + 'umbral_model_frecuencia_medico_30D.pkl', 'days': 30},
            {'path': base_path + 'umbral_model_frecuencia_F_30D_medico.pkl', 'days': 30},
            {'path': base_path + 'umbral_model_frecuencia_J_30D_medico.pkl', 'days': 30},
            {'path': base_path + 'umbral_model_frecuencia_M_30D_medico.pkl', 'days': 30},
            {'path': base_path + 'umbral_model_n_remotas_30D.pkl', 'days': 30},
            {'path': base_path + 'umbral_model_n_presenciales_30D.pkl', 'days': 30}
        ]        

        # Aplicar modelos secuencialmente sobre el mismo df
        for config in models_config:
            df = apply_model(df, config)

        return df

    except Exception as e:
        umbrales_logger.error(f"Error procesando datos de umbral: {str(e)}")
        raise


def process_umbral_and_save_db(data_df, dias, entity_col):
    print(f"DEBUG: process_umbral_and_save_db alcanzado (PID: {os.getpid()}).")
    umbrales_umbrales_logger.info(f"Inicia cálculo y guardado de umbrales. Parámetros: dias={dias}, entidad={entity_col}, registros_iniciales={len(data_df)}.")
    sys.modules['__main__'].Umbrales = Umbrales
    try:
        df_processed = process_umbral_data(data_df)
        umbrales_umbrales_logger.info(f"Procesamiento de datos de umbral finalizado. Se procesaron {len(df_processed)} registros.")
        
        # La función insert_umbrales es llamada aquí, pero su log va al umbrales_logger principal.
        # Podríamos agregar un log aquí después de la inserción si es necesario.
        insert_umbrales(df_processed, fecha=data_df['fecha_emision'].iloc[0] if not data_df.empty else None, dias=dias, columna_entidad=entity_col)
        
        umbrales_umbrales_logger.info(f"Finaliza el guardado de {len(df_processed)} registros de umbrales en la base de datos.")
    except Exception as e:
        umbrales_umbrales_logger.error(f"Error en la ejecución de UMBRALES: {str(e)}", exc_info=True)
        # También se loggea en el umbrales_logger general para visibilidad en la consola principal
        umbrales_logger.error(f"Error en la ejecución UMBRALES, no fue posible guardar en base de datos: {str(e)}")