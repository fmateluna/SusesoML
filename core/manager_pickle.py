from datetime import datetime
import sys
import dill as pickle
from pathlib import Path
import pandas as pd
import asyncio
import threading
import logging
from core.services import  query_masivo, update_propensity_score_licencias
import copy
import threading

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


result_map_lock = threading.Lock()
result_map = {}

class BusinessModel:
    def __init__(self, hyperparameters):
        """
        Inicializa el modelo con los hiperparámetros.
        """
        self.hyperparameters = hyperparameters

    def preprocess(self, df):
        """
        Limita días de reposo y convierte fechas.
        """
        df = df[df['dias_reposo'] <= 365]
        df['fecha_emision'] = pd.to_datetime(df['fecha_emision'], errors='coerce')
        return df

    def apply_business_rule(self, df):
        """
        Aplica la regla de negocio usando condiciones sobre especialidad, diagnóstico y días de reposo.
        """
        filtro = self.hyperparameters['filter']
        nombre_columna = self.hyperparameters['name']
        limite = self.hyperparameters['below_limit']

        df = df.copy()
        df[nombre_columna] = 0
        df['especialidad_profesional'] = df['especialidad_profesional'].fillna("")

        condiciones_especialidad = df['especialidad_profesional'].isin(filtro['especialidad_profesional'])
        condiciones_diagnostico = df['cod_diagnostico_principal'].astype(str).str.startswith(filtro['cod_diagnostico_principal'])
        condiciones_dias = df['dias_reposo'] >= limite

        df.loc[condiciones_especialidad & condiciones_diagnostico & condiciones_dias, nombre_columna] = 1
        return df

    def predict_prob(self, df):
        """
        Aplica preprocesamiento y luego la regla de negocio.
        """
        df = self.preprocess(df)
        df = self.apply_business_rule(df)
        return df

sys.modules['__main__'].BusinessModel = BusinessModel



class ManagerPickle:
    def __init__(self):
        """
        Inicializa el administrador con una lista de modelos y carga los modelos pickle en memoria.
        """
        self.model_names = ["business_model_rn_1.pkl", "business_model_rn_2.pkl"]
        #result_map = {}
        self._active_tasks = {}
        self.modelos_cargados = {}

        # Cargar los modelos pickle una sola vez
        for model_name in self.model_names:
            pickle_path = f"repo_pickle/{model_name}"
            pickle_path_file = Path(pickle_path)
            try:
                if not pickle_path_file.exists():
                    raise FileNotFoundError(f"El archivo {model_name} no se encuentra en {pickle_path}")
                with open(pickle_path, "rb") as modelo:
                    self.modelos_cargados[model_name] = pickle.load(modelo)
                logger.info(f"Modelo {model_name} cargado exitosamente")
            except Exception as e:
                logger.error(f"Error al cargar el modelo {model_name}: {str(e)}")
                raise

    def _generate_request_key(self, fecha_inicio: str, fecha_fin: str) -> str:
        """
        Genera una clave única basada en fecha_inicio y fecha_fin.
        """
        return f"{fecha_inicio}_{fecha_fin}"

    def ejecuta_regla_negocio(self, pickle_name: str, datos_licencias: pd.DataFrame, parametros_licencia: pd.Series, rn: int) -> pd.DataFrame:
        """
        Ejecuta la regla de negocio usando un modelo pre-cargado y retorna un DataFrame.
        """
        columnas = ["id_licencia", "dias_reposo", "fecha_emision", "fecha_inicio_reposo", "especialidad_profesional", "cod_diagnostico_principal"]
        data = datos_licencias[columnas]
        score_name = f'propensity_score_rn_{rn}'

        try:
            params_dict = parametros_licencia.to_dict()
            modelo_cargado = self.modelos_cargados[pickle_name]
            resultados = modelo_cargado.predict_prob(data)
            resultados["folio"] = params_dict["folio"]
            logger.info(f"Resultados para id_licencia {params_dict['id_licencia']}: {resultados[['id_licencia', 'dias_reposo','especialidad_profesional', 'cod_diagnostico_principal',score_name]].to_dict(orient='records')}")
            return resultados
        except KeyError as e:
            logger.error(f"Falta la clave {e} en parametros_licencia para id_licencia {params_dict.get('id_licencia', 'desconocido')}")
            return pd.DataFrame()
        except TypeError as e:
            logger.error(f"Error en los parámetros de predict_prob: {e} para id_licencia {params_dict.get('id_licencia', 'desconocido')}")
            return pd.DataFrame()
        except AttributeError as e:
            logger.error(f"Error al usar el modelo: {e} para id_licencia {params_dict.get('id_licencia', 'desconocido')}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error inesperado: {e} para id_licencia {params_dict.get('id_licencia', 'desconocido')}")
            return pd.DataFrame()

    def consulta_ejecuta_masivo(self, fecha_inicio: str, fecha_fin: str) -> dict:
        request_key = self._generate_request_key(fecha_inicio, fecha_fin)
        with result_map_lock:
            if request_key in result_map:
                # Retorna una copia inmutable!!!!!
                return copy.deepcopy(result_map[request_key])
            else:
                return {'status': 'not_found', 'rules_executed': []}

    def ejecuta_masivo(self, fecha_inicio: str, fecha_fin: str) -> dict:
        
    
   
        
        request_key = self._generate_request_key(fecha_inicio, fecha_fin)
        
        with result_map_lock:
            if request_key in result_map:
                return copy.deepcopy(result_map[request_key])
            
            # Inicializa nuevo estado
            result_map[request_key] = {
                'status': 'starting',
                'rules_executed': 0
            }
            # Crea copia para la respuesta
            response_copy_pal_front = copy.deepcopy(result_map[request_key])
        
        def run_background():
            result_map[request_key]['status']="extract_data"
            datos_licencias = query_masivo(fecha_inicio, fecha_fin)            
            try:
                asyncio.run(self.ini_ejecuta_masivo(datos_licencias, fecha_inicio, fecha_fin))
            except Exception as e:
                logger.error(f"Error en run_background: {str(e)}")
                with result_map_lock:
                    result_map[request_key] = {
                        'status': 'error',
                        'rules_executed': 0,
                        # 'data': [],
                        'reason': str(e)
                    }
                    
        thread = threading.Thread(target=run_background)
        self._active_tasks[request_key] = thread
        thread.start()
     
        return response_copy_pal_front

    async def ini_ejecuta_masivo(self, datos_licencias: pd.DataFrame, fecha_inicio: str, fecha_fin: str) -> dict:
        """
        Ejecuta las reglas de negocio de forma masiva, enviando resultados a la base de datos en bloques.
        """
        request_key = self._generate_request_key(fecha_inicio, fecha_fin)
        columnas = ["id_licencia", "dias_reposo", "fecha_emision", "fecha_inicio_reposo", "especialidad_profesional", "cod_diagnostico_principal", "folio"]
        results = []
        batch_results = []
        block_size = 100  # Guardar cada 100 cálculos

        try:
            if not all(col in datos_licencias.columns for col in columnas):
                raise ValueError(f"Faltan columnas: {set(columnas) - set(datos_licencias.columns)}")
            
            count_rn_exe = {}
            current_state = {}
            for index, licencia in datos_licencias.iterrows():
                for rn, model_name in enumerate(self.model_names, start=1):
                    try:
                        single_row_df = datos_licencias.loc[[index], columnas]
                        score_name = f'propensity_score_rn_{rn}'
                        result = self.ejecuta_regla_negocio(model_name, single_row_df, licencia, rn)
                        
                        
                        if not result.empty:
                            batch_results.append((result, score_name, rn))
                                       
                        # Guardar en la base de datos cada block_size cálculos
                        if len(batch_results) >= block_size:
                            logger.info(f"Guardando bloque de {len(batch_results)} resultados")
                            for batch_result, batch_score_name, batch_rn in batch_results:
                                update_propensity_score_licencias(batch_result, batch_score_name, batch_rn)
                            batch_results = []  # Limpiar el lote
                            
                        if model_name not in count_rn_exe:
                            count_rn_exe[model_name] = 0
                        count_rn_exe[model_name]=count_rn_exe[model_name]+1

                        current_state['status']='execute'
                        current_state['total']=len(datos_licencias)
                        current_state[model_name]= count_rn_exe[model_name] 
                        result_map[request_key] = current_state
                        
                        
                    except Exception as e:
                        logger.error(f"Error en registro {index}, modelo {model_name}: {str(e)}")


            # Guardar cualquier resultado restante
            if batch_results:
                logger.info(f"Guardando bloque final de {len(batch_results)} resultados")
                for batch_result, batch_score_name, batch_rn in batch_results:
                    update_propensity_score_licencias(batch_result, batch_score_name, batch_rn)

            with result_map_lock:
                result_map[request_key]['status']='completed'
        except Exception as e:
            logger.error(f"Error en ini_ejecuta_masivo: {str(e)}")
            with result_map_lock:
                result_map[request_key]['status']='error'
                result_map[request_key]['reason']=str(e)
        finally:
            if request_key in self._active_tasks:
                del self._active_tasks[request_key]
        
        return result_map[request_key]

    def get_results_by_request(self, fecha_inicio: str, fecha_fin: str) -> dict:
        request_key = self._generate_request_key(fecha_inicio, fecha_fin)
        return result_map.get(request_key, {'status': 'not_found', 'rules_executed': []})