from datetime import datetime
from pathlib import Path
import pandas as pd
import inspect
import asyncio
from core.services import update_propensity_score_licencias

class BusinessRuleModel:
    def __init__(self, df):
        """
        Inicializa el modelo con un DataFrame.

        Args:
            df (pd.DataFrame): El DataFrame de entrada.
        """
        self.df = df
        self._preprocess()

    def _preprocess(self):
        """
        Preprocesa el DataFrame: limita los días de reposo y convierte las fechas.
        """
        # Limitar días de reposo
        self.df = self.df[self.df['dias_reposo'] <= 365]

        # Convertir formato de fechas
        self.df['fecha_emision'] = pd.to_datetime(self.df['fecha_emision'], errors='coerce')
        self.df['fecha_inicio_reposo'] = pd.to_datetime(self.df['fecha_inicio_reposo'], errors='coerce')

    def apply_business_rule(self, filter, name, below_limit):
        """
        Aplica una regla de negocio al DataFrame.

        Args:
            filter (dict): Criterios de filtrado (especialidad, código de diagnóstico).
            name (str): Nombre de la nueva columna a agregar.
            below_limit (int): Umbral para los días de reposo.

        Returns:
            pd.DataFrame: El DataFrame modificado.
        """
        df_filter = self.df.copy()
        df_filter[name] = 0

        df_filter.loc[
            (df_filter['especialidad_profesional'] == filter['especialidad_profesional']) &
            (df_filter['cod_diagnostico_principal'].str.startswith(filter['cod_diagnostico_principal'])) &
            (df_filter['dias_reposo'] >= below_limit),
            name
        ] = 1

        self.df = df_filter
        return self.df

    def predict_prob(self, filter, name, below_limit):
        """
        Calcula una puntuación de propensión según una regla de negocio.

        Args:
            filter (dict): Criterios de filtrado (especialidad, código de diagnóstico).
            name (str): Nombre de la columna para almacenar la puntuación.
            below_limit (int): Umbral para los días de reposo.

        Returns:
            pd.DataFrame: El DataFrame con la columna de puntuación.
        """
        return self.apply_business_rule(filter, name, below_limit)



class ManagerPickle:
    def __init__(self, pickle_path: str = "business_rule_model"):
        self.pickle_path = Path(pickle_path)
        # Mapa para almacenar resultados en memoria
        self.result_map = {}

    def _generate_request_key(self, fecha_inicio: str, fecha_fin: str) -> str:
        """Genera una clave única basada en fecha_inicio y fecha_fin."""
        return f"{fecha_inicio}_{fecha_fin}"

    def ejecuta_regla_negocio1(self, pickle_name, datos_licencias: pd.DataFrame, nombre_columna, cod_diagnostico_principal, especialidad_profesional: str) -> list[dict]:
        pickle_path = f"repo_pickle/{pickle_name}.pkl"        
        self.pickle_path = Path(pickle_path)
        columnas = ["id_licencia", "dias_reposo", "fecha_emision", "fecha_inicio_reposo", "especialidad_profesional", "cod_diagnostico_principal"]
        data = datos_licencias[columnas]
        try:
            modelo_cargado = BusinessRuleModel(data)
            filtro = {
                "especialidad_profesional": especialidad_profesional,
                "cod_diagnostico_principal": cod_diagnostico_principal
            }
            umbral_dias = 30
            
            resultados = modelo_cargado.predict_prob(filtro, nombre_columna, umbral_dias)            
            #print("DataFrame con la nueva columna de puntuación:\n", resultados)
            update_propensity_score_licencias(resultados, datos_licencias, nombre_columna, 1) 

        except TypeError as e:
            print(f"Error en los parámetros de predict_prob: {e}. Verifica que filter, name y below_limit sean correctos.")
        except Exception as e:
            print(f"Error inesperado: {e}. Verifica los datos o la compatibilidad del modelo.")  
            
        return resultados.to_dict(orient='records')
    
    def ejecuta_masivo(self, datos_licencias: pd.DataFrame, fecha_inicio: str, fecha_fin: str) -> dict:
        request_key = self._generate_request_key(fecha_inicio, fecha_fin)
        

        self._masivo_task = asyncio.create_task(self.ini_ejecuta_masivo(datos_licencias, fecha_inicio, fecha_fin))

        return self.result_map.get(request_key, {'status': 'not_found', 'rules_executed': [], 'data': []})
   
   
    def ini_ejecuta_masivo(self, datos_licencias: pd.DataFrame, fecha_inicio: str, fecha_fin: str) -> dict:
        request_key = self._generate_request_key(fecha_inicio, fecha_fin)
        columnas = ["id_licencia", "dias_reposo", "fecha_emision", "fecha_inicio_reposo", "especialidad_profesional", "cod_diagnostico_principal"]
        data = datos_licencias[columnas]

        # Obtener todas las reglas 'ejecuta_regla_negocio'
        regla_methods = [
            method for method_name, method in inspect.getmembers(self, predicate=inspect.ismethod)
            if method_name.startswith('ejecuta_regla_negocio')
        ]

        # Parámetros predeterminados para las reglas
        default_params = {
            'pickle_name': 'business_rule_model',
            'nombre_columna': 'score_regla',
            'cod_diagnostico_principal': 'default_code',  
            'especialidad_profesional': 'default_specialty'  
        }

        # Ejecutar todas las reglas de negocio
        results = []
        for method in regla_methods:
            try:
                sig = inspect.signature(method)
                if set(['pickle_name', 'datos_licencias', 'nombre_columna', 'cod_diagnostico_principal', 'especialidad_profesional']).issubset(sig.parameters):
                    result = method(
                        default_params['pickle_name'],
                        datos_licencias,
                        default_params['nombre_columna'],
                        default_params['cod_diagnostico_principal'],
                        default_params['especialidad_profesional']
                    )
                    results.append({
                        'regla': method.__name__,
                        'status': 'executed',
                        'data': result
                    })
                else:
                    results.append({
                        'regla': method.__name__,
                        'status': 'skipped',
                        'reason': 'Incompatible parameters'
                    })
            except Exception as e:
                results.append({
                    'regla': method.__name__,
                    'status': 'error',
                    'reason': str(e)
                })

            # Actualizar el mapa con los resultados
            self.result_map[request_key] = {
                'status': 'executing' if results else 'no_rules_found',
                'rules_executed': results,
                'data': data.to_dict(orient='records')
            }

        return self.result_map.get(request_key, {'status': 'not_found', 'rules_executed': [], 'data': []})

    def get_results_by_request(self, fecha_inicio: str, fecha_fin: str) -> dict:
        """Consulta los resultados almacenados para un request específico."""
        request_key = self._generate_request_key(fecha_inicio, fecha_fin)
        return self.result_map.get(request_key, {'status': 'not_found', 'rules_executed': [], 'data': []})