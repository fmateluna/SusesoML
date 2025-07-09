from datetime import datetime
from pathlib import Path
from typing import Hashable
import pandas as pd
import asyncio
import threading
from core.services import update_propensity_score_licencias

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

    def ejecuta_regla_negocio(self, pickle_name: str, datos_licencias: pd.DataFrame, nombre_columna : str, parametros_licencia : tuple[Hashable, pd.Series], rn: int) -> list[dict]:
        """
        Ejecuta una regla de negocio y actualiza propensity_score con el rn especificado.

        Args:
            pickle_name (str): Nombre del archivo pickle.
            datos_licencias (pd.DataFrame): DataFrame con datos de licencias.
            nombre_columna (str): Nombre de la columna de puntuación.
            cod_diagnostico_principal (str): Código de diagnóstico principal.
            especialidad_profesional (str): Especialidad profesional.
            rn (int): Identificador de la regla (1 o 2).

        Returns:
            list[dict]: Resultados de la regla en formato de lista de diccionarios.
        """
        #pickle_path = f"repo_pickle/{pickle_name}"
        
        columnas = ["id_licencia", "dias_reposo", "fecha_emision", "fecha_inicio_reposo", "especialidad_profesional", "cod_diagnostico_principal","folio"]
        data = datos_licencias[columnas]
        try:
            hyperparameters = {
                'filter': {
                    'especialidad_profesional': [parametros_licencia["especialidad_profesional"]], 
                    'cod_diagnostico_principal': parametros_licencia["cod_diagnostico_principal"]
                },
                'name': nombre_columna,
                'below_limit': parametros_licencia["dias_reposo"]
            }
            modelo_cargado = BusinessModel(hyperparameters)
            resultados = modelo_cargado.predict_prob(data)
            update_propensity_score_licencias(resultados, nombre_columna, rn)
            return resultados.to_dict(orient='records')
        except TypeError as e:
            print(f"Error en los parámetros de predict_prob: {e}. Verifica que filter, name y below_limit sean correctos.")
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
                        'score_regla',
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