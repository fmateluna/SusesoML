import sys
import pandas as pd
import numpy as np
import logging
import pickle as pkl
import os

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
logger = logging.getLogger(__name__)

def apply_model(df, config):
    """Función para aplicar un modelo."""
    model_path = config['path']
    try:
        logger.info(f"Ejecutando MODELO {model_path}")
        model = pkl.load(open(model_path, 'rb'))
        if hasattr(model, 'window_days') and model.window_days != config['days']:
            logger.warning(f"El modelo en {model_path} tiene window_days={model.window_days}, esperado {config['days']}.")
        
        # Fit y predict_proba, agregando la columna de score
        model.fit(df)
        if hasattr(model, 'col_frecuencia'):
            filename = os.path.basename(model_path) 
            base_name = filename.replace("umbral_model_", "").replace(".pkl", "")

            # Generar nombre de la columna con prefijo "score_"
            score_col = f"score_{base_name}"


            df[score_col] = model.predict_proba(df)
            logger.info(f"Modelo {model_path} aplicado. Columna agregada: {score_col}")
        else:
            logger.warning(f"El modelo en {model_path} no tiene 'col_frecuencia'.")
        return df
    except Exception as e:
        logger.error(f"Error al aplicar modelo {model_path}: {str(e)}")
        return df  # Retorna df sin cambios en caso de error

def process_umbral_data(df, entity_col='rut_medico', base_path=None):
    try:
        if base_path is None:
            # Obtener el directorio del archivo Python actual de manera dinámica
            base_path = os.path.dirname(os.path.abspath(__file__)) + '/'        
        # Aplicar filtros iniciales
        df = df[df['dias_reposo'] <= 365]
        df = df[~df['cod_diagnostico_principal'].isin(['U07.1', 'U07.2'])]
        df['fecha_emision'] = pd.to_datetime(df['fecha_emision'], errors='coerce')
        df = df.sort_values(by=[entity_col, 'rut_trabajador', 'fecha_emision']).reset_index(drop=True)

        # Lista de modelos
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
        logger.error(f"Error procesando datos de umbral: {str(e)}")
        raise

def csv_to_results_umbrales(data_csv_path, result_csv_path):
    sys.modules['__main__'].Umbrales = Umbrales
    try:
        df = pd.read_csv(data_csv_path)
        logger.info("DataFrame leído exitosamente del CSV.")
        #print("DataFrame original:")
        #print(df)

        df_processed = process_umbral_data(df)
        logger.info("Procesamiento completado. DataFrame procesado:")
        print(df_processed)

        """
        new_columns = [col for col in df_processed.columns if col not in expected_columns]
        if new_columns:
            logger.info(f"Columnas nuevas agregadas: {new_columns}")
            print("Columnas nuevas y valores:")
            print(df_processed[new_columns])
        else:
            logger.warning("No se agregaron columnas nuevas. Verifica los modelos.")
        """
        df_processed.to_csv(result_csv_path, index=False)
        logger.info(f"Resultado guardado en {result_csv_path}")

    except Exception as e:
        logger.error(f"Error en la ejecución standalone: {str(e)}")    

# Código standalone
if __name__ == "__main__":
    sys.modules['__main__'].Umbrales = Umbrales
    csv_path = 'process_data.csv'  # Ajusta si es necesario
    try:
        df = pd.read_csv(csv_path)
        logger.info("DataFrame leído exitosamente del CSV.")
        print("DataFrame original:")
        print(df)

        expected_columns = [
            'id_licencia', 'folio', 'dias_reposo', 'fecha_emision', 'fecha_inicio_reposo',
            'especialidad_profesional', 'cod_diagnostico_principal', 'rut_medico',
            'rut_trabajador', 'marca_otorgamiento', 'frecuencia_medico_30D',
            'frecuencia_medico_15D', 'frecuencia_medico_7D', 'frecuencia_J_60D_medico',
            'frecuencia_F_60D_medico', 'frecuencia_M_60D_medico', 'n_remotas_60D',
            'n_presenciales_60D'
        ]
        if not all(col in df.columns for col in expected_columns):
            raise ValueError("El CSV no contiene todas las columnas esperadas.")
        logger.info("Columnas del CSV verificadas correctamente.")

        df_processed = process_umbral_data(df)
        logger.info("Procesamiento completado. DataFrame procesado:")
        print(df_processed)

        new_columns = [col for col in df_processed.columns if col not in expected_columns]
        if new_columns:
            logger.info(f"Columnas nuevas agregadas: {new_columns}")
            print("Columnas nuevas y valores:")
            print(df_processed[new_columns])
        else:
            logger.warning("No se agregaron columnas nuevas. Verifica los modelos.")
        
        # Guardar el resultado en un CSV con sufijo _result
        result_path = os.path.splitext(csv_path)[0] + '_result.csv'
        df_processed.to_csv(result_path, index=False)
        logger.info(f"Resultado guardado en {result_path}")

    except Exception as e:
        logger.error(f"Error en la ejecución standalone: {str(e)}")