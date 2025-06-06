from datetime import datetime
import pickle
from pathlib import Path
import random
import pandas as pd

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

    def execute(self, pickle_name, method_name, *args):
        pickle_path = f"repo_pickle/{pickle_name}.pkl"        
        self.pickle_path = Path(pickle_path)
        # Columnas necesarias para la predicción
        columnas = ["id_licencia", "dias_reposo", "fecha_emision", "fecha_inicio_reposo", "especialidad_profesional", "cod_diagnostico_principal"]

        Datos_licencias = pd.DataFrame({
            "id_licencia": ["LIC001", "LIC002", "LIC003"],
            "dias_reposo": [7, 14, 5],
            "fecha_emision": ["2025-06-01", "2025-06-02", "2025-06-03"],
            "fecha_inicio_reposo": ["2025-06-02", "2025-06-03", "2025-06-04"],
            "especialidad_profesional": ["Traumatología", "Cardiología", "Medicina General"],
            "cod_diagnostico_principal": ["S93.4", "I20.9", "J45"]
        })


        # Seleccionar las columnas relevantes
        data = Datos_licencias[columnas]
        
        try:
            # Inicializar el modelo con el DataFrame
            modelo_cargado = BusinessRuleModel(data)

            # Definir parámetros para la regla de negocio
            filtro = {
                "especialidad_profesional": "Traumatología",
                "cod_diagnostico_principal": "S93"
            }
            nombre_columna = "puntuacion_traumatologia"
            umbral_dias = 7

            # Aplicar la regla de negocio usando predict_prob
            resultados = modelo_cargado.predict_prob(filtro, nombre_columna, umbral_dias)

            # Imprimir resultados
            print("DataFrame con la nueva columna de puntuación:\n", resultados)

        except TypeError as e:
            print(f"Error en los parámetros de predict_prob: {e}. Verifica que filter, name y below_limit sean correctos.")
        except Exception as e:
            print(f"Error inesperado: {e}. Verifica los datos o la compatibilidad del modelo.")  
            
            
                  
""""
        try:
            with open(pickle_path, 'rb') as file:
                loaded_object = pickle.load(file)
        except Exception as e:
            return f"Error al cargar el archivo pickle: {e}"

        # Verificamos si el método existe en el objeto cargado
        if hasattr(loaded_object, method_name) and callable(getattr(loaded_object, method_name)):
            # Ejecutamos el método con los parámetros que se pasan como *args
            method = getattr(loaded_object, method_name)
            return method(*args)
        else:
            return f"El método '{method_name}' no existe en el objeto cargado."
"""