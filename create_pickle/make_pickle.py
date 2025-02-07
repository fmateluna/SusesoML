import pickle
import random
from datetime import datetime

# Clase que contiene el método consulta
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

# Crear una instancia del objeto
business_model = BusinessModel()

# Guardamos el objeto completo en un archivo pickle
with open('businessModel.pkl', 'wb') as file:
    pickle.dump(business_model, file)

# Cargar el pickle y ejecutar el método consulta del objeto cargado
with open('businessModel.pkl', 'rb') as file:
    loaded_object = pickle.load(file)

# Parámetros de entrada
folios = ["14504228-3", "13304228-3", "11511228-4"]
fecha_inicio = "2015-01-01"
fecha_fin = "2020-12-31"

# Ejecutar el método consulta del objeto cargado
result = loaded_object.consulta(folios, fecha_inicio, fecha_fin)

# Imprimir el resultado
print(result)
