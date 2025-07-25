import pandas as pd

class BusinessModel:
    def __init__(self, hyperparameters):
        """
        Inicializa el modelo con los hiperparámetros.
        """
        BusinessModel.__module__ = '__main__'
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
