
import numpy as np
import pandas as pd

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
