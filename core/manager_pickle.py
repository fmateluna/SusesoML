from datetime import datetime
import dill as pickle
from pathlib import Path
from typing import Hashable
import pandas as pd
import asyncio
import threading
from core.services import update_propensity_score_licencias
from models import BusinessModel

hyperparameters = {
    'filter': {
        'especialidad_profesional': ['Cardiología', 'Cardiologia ', 'Cardiologo'],
        'cod_diagnostico_principal': 'F'
    },
    'name': 'puntuacion_Cardiología',
    'below_limit': 7
}

class ManagerPickle:
    def __init__(self):
        """
        Inicializa el administrador con una lista de modelos y mapas para resultados y tareas.
        """
        self.model_names = ["business_model_rn_1.pkl", "business_model_rn_2.pkl"]
        self.result_map = {}
        self._active_tasks = {}

    def _generate_request_key(self, fecha_inicio: str, fecha_fin: str) -> str:
        """
        Genera una clave única basada en fecha_inicio y fecha_fin.
        """
        return f"{fecha_inicio}_{fecha_fin}"

    def ejecuta_regla_negocio(self, pickle_name: str, datos_licencias: pd.DataFrame, parametros_licencia: pd.Series, rn: int) -> list[dict]:
        pickle_path = f"repo_pickle/{pickle_name}"            
        pickle_path_file = Path(pickle_path)        
        # Verificar si el archivo pickle existe
        if not pickle_path_file.exists():
            raise FileNotFoundError(f"El archivo {pickle_name} no se encuentra en {pickle_path}")
        
        columnas = ["id_licencia", "dias_reposo", "fecha_emision", "fecha_inicio_reposo", "especialidad_profesional", "cod_diagnostico_principal"]
        data = datos_licencias[columnas]
        below_limit=30
        score_name =  f'propensity_score_rn_{rn}'
        
        if rn==1:
            below_limit = 30
        
        if rn==2:
            below_limit = 30
        

        try:
            # Convertir la serie a diccionario para mayor robustez
            params_dict = parametros_licencia.to_dict()
            hyperparameters = {
                'filter': {
                    'especialidad_profesional': [params_dict["especialidad_profesional"]], 
                    'cod_diagnostico_principal': params_dict["cod_diagnostico_principal"]
                },
                'name': score_name,
                'below_limit': below_limit
            }

            #modelo_cargado = BusinessModel(hyperparameters)
            
            with open(pickle_path, "rb") as modelo:
                modelo_cargado = pickle.load(modelo)
            resultados = modelo_cargado.predict_prob(data)
            resultados["folio"] = params_dict["folio"]
            update_propensity_score_licencias(resultados, score_name, rn)
            return resultados.to_dict(orient='records')
        except KeyError as e:
            print(f"Error: Falta la clave {e} en parametros_licencia.")
            return []
        except TypeError as e:
            print(f"Error en los parámetros de predict_prob: {e}. Verifica que filter, name y below_limit sean correctos.")
            return []
        except FileNotFoundError as e:
            print(f"Error: {e}")
            return []
        except AttributeError as e:
            print(f"Error al cargar el modelo: {e}. Asegúrate de que el archivo pickle fue creado con la clase BusinessModel definida en este script.")
            return []
        except Exception as e:
            print(f"Error inesperado: {e}. Verifica los datos o la compatibilidad del modelo.")
            return []
        
    def ejecuta_masivo(self, datos_licencias: pd.DataFrame, fecha_inicio: str, fecha_fin: str) -> dict:
        """
        Inicia la ejecución masiva de reglas de negocio de forma asíncrona.

        Args:
            datos_licencias (pd.DataFrame): DataFrame con los datos de licencias.
            fecha_inicio (str): Fecha de inicio para la clave de solicitud.
            fecha_fin (str): Fecha de fin para la clave de solicitud.

        Returns:
            dict: Estado de la ejecución masiva.
        """
        request_key = self._generate_request_key(fecha_inicio, fecha_fin)
        if len(self.result_map)>0 and self.result_map[request_key]:
            return self.result_map[request_key]
        
        self.result_map[request_key] = {
            'status': 'starting',
            'rules_executed': [],
            'data': []
        }
        """
        self._active_tasks[request_key] = asyncio.create_task(
            self.ini_ejecuta_masivo(datos_licencias, fecha_inicio, fecha_fin)
        )
        """
        
        
        def run_background():
            asyncio.run(self.ini_ejecuta_masivo(datos_licencias, fecha_inicio, fecha_fin))

        thread = threading.Thread(target=run_background)
        thread.start()
     
        return {
            'status': 'in process',
            'detail': 'Ejecución masiva iniciada',
            'rules_executed': [],
            'data': []
        }

    async def ini_ejecuta_masivo(self, datos_licencias: pd.DataFrame, fecha_inicio: str, fecha_fin: str) -> dict:
        """
        Ejecuta las reglas de negocio de forma masiva de manera asíncrona para ambos modelos, iterando por cada fila.

        Args:
            datos_licencias (pd.DataFrame): DataFrame con los datos de licencias.
            fecha_inicio (str): Fecha de inicio para la clave de solicitud.
            fecha_fin (str): Fecha de fin para la clave de solicitud.

        Returns:
            dict: Resultados de la ejecución masiva.
        """
        request_key = self._generate_request_key(fecha_inicio, fecha_fin)
        columnas = ["id_licencia", "dias_reposo", "fecha_emision", "fecha_inicio_reposo", "especialidad_profesional", "cod_diagnostico_principal","folio"]
        data = datos_licencias[columnas]
        results = []

        # Iterar sobre cada fila de datos_licencias
        for index, row in datos_licencias.iterrows():
            for rn, model_name in enumerate(self.model_names, start=1):
                try:
                    # Crear un DataFrame con una sola fila para la regla
                    single_row_df = datos_licencias.loc[[index], columnas]
                    result = self.ejecuta_regla_negocio(
                        model_name,
                        single_row_df,
                        row,
                        rn
                    )
                    results.append({
                        'regla': f"ejecuta_regla_negocio_{model_name}_id_{row['id_licencia']}",
                        'status': 'executed',
                        'data': result
                    })
                    self.result_map[request_key] = {
                        'status': 'still working',
                        'rules_executed': results,
                        'data': data.to_dict(orient='records') 
                    }                  
                except Exception as e:
                    results.append({
                        'regla': f"ejecuta_regla_negocio_{model_name}_id_{row['id_licencia']}",
                        'status': 'error',
                        'reason': str(e)
                    })

        self.result_map[request_key] = {
            'status': 'completed' if results else 'no_rules_found',
            'rules_executed': results,
            'data': data.to_dict(orient='records')
        }
        if request_key in self._active_tasks:
            del self._active_tasks[request_key]
        return self.result_map[request_key]

    def get_results_by_request(self, fecha_inicio: str, fecha_fin: str) -> dict:
        """
        Consulta los resultados almacenados para un request específico.

        Args:
            fecha_inicio (str): Fecha de inicio para la clave de solicitud.
            fecha_fin (str): Fecha de fin para la clave de solicitud.

        Returns:
            dict: Resultados almacenados o estado 'not_found' si no existen.
        """
        request_key = self._generate_request_key(fecha_inicio, fecha_fin)
        return self.result_map.get(request_key, {'status': 'not_found', 'rules_executed': [], 'data': []})