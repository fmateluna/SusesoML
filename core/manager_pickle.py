from datetime import datetime
import pickle
from pathlib import Path
import random

class BusinessModel:
    def consulta(self, folios, fecha_inicio, fecha_fin):
        # Convertir las fechas de string a datetime para comparar
        fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d")

        # Simulamos que estamos filtrando licencias (en este caso solo retornamos un código aleatorio)
        result = {
            "message": "Éxito",
            "folios": folios,
            "fecha_inicio": fecha_inicio.strftime("%Y-%m-%d"),
            "fecha_fin": fecha_fin.strftime("%Y-%m-%d"),
            "codigo_random": random.randint(1000, 9999)
        }
        return result

class ManagerPickle:
    def __init__(self, pickle_path: str = "repo_pickle"):
        self.pickle_path = Path(pickle_path)

    def execute(self, pickle_name, method_name, *args):
        pickle_path = f"repo_pickle/{pickle_name}.pkl"
        
        # Intentamos cargar el archivo pickle
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