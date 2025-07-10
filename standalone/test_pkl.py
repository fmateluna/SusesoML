import dill as pickle
import pandas as pd
import random

# Definición de la clase BusinessModel
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

# Crear un DataFrame de ejemplo para Datos_licencias
codigos_cardiologia = [
    "I10",   # Hipertensión esencial
    "I20.0", # Angina inestable
    "I21.9", # Infarto agudo de miocardio, sin especificar
    "I50.0", # Insuficiencia cardíaca congestiva
    "I48.0", # Fibrilación auricular
    "I25.9", # Enfermedad isquémica crónica del corazón
    "I47.1", # Taquicardia supraventricular
    "I49.9", # Trastorno del ritmo cardíaco, no especificado
    "I70.2", # Aterosclerosis de las arterias del corazón
    "R07.9", # Dolor torácico, no especificado
]

Datos_licencias = pd.DataFrame({
    "id_licencia": [f"LIC{str(i).zfill(3)}" for i in range(1, 31)],
    "dias_reposo": [random.randint(5, 20) for _ in range(30)],
    "fecha_emision": pd.date_range(start="2025-06-01", periods=30).strftime("%Y-%m-%d"),
    "fecha_inicio_reposo": pd.date_range(start="2025-06-02", periods=30).strftime("%Y-%m-%d"),
    "especialidad_profesional": ["Cardiología"] * 30,
    "cod_diagnostico_principal": [random.choice(codigos_cardiologia) for _ in range(30)]
})

# Columnas necesarias para la predicción
columnas = ["id_licencia", "dias_reposo", "fecha_emision", "fecha_inicio_reposo", "especialidad_profesional", "cod_diagnostico_principal"]

# Seleccionar las columnas relevantes
data = Datos_licencias[columnas]

# Definir los hiperparámetros
hyperparameters = {
    'filter': {
        'especialidad_profesional': ['Cardiología', 'Cardiologia ', 'Cardiologo'],
        'cod_diagnostico_principal': 'F'
    },
    'name': 'puntuacion_Cardiología',
    'below_limit': 30
}

# Opción 1: Crear una nueva instancia de BusinessModel con los hiperparámetros
modelo = "./TEST_PKL/business_model_rn_1.pkl"
try:
    # Inicializar el modelo con los hiperparámetros
    with open(modelo, "rb") as archivo:
        modelo_cargado = pickle.load(archivo)

    # Aplicar la regla de negocio usando predict_prob
    resultados = modelo_cargado.predict_prob(data)

    # Imprimir resultados
    print("DataFrame con la nueva columna de puntuación:\n", resultados)

except Exception as e:
    print(f"Error inesperado: {e}. Verifica los datos o la compatibilidad del modelo.")