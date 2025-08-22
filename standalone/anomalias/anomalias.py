import os
import pickle as pkl
import pandas as pd
import numpy as np
from typing import List, Optional, Tuple

from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import IsolationForest


class AnomaliesModel:
    """
    Modelo para detección de anomalías utilizando IsolationForest sobre un conjunto fijo de atributos.

    Flujo:
      - Selección/creación de columnas esperadas
      - Normalización MinMax
      - Entrenamiento y scoring con IsolationForest
      - Cálculo del propensity score (0..1) basado en la función de decisión
    """

    def __init__(
        self,
        feature_columns: Optional[List[str]] = None,
        n_estimators: int = 100,
        contamination: str | float = "auto",
        random_state: int = 42,
    ) -> None:
        if feature_columns is None:
            feature_columns = [
                'dias_reposo', 'edad_trabajador', 'hora_emision', 'dia_codificado',
                'calidad_Trabajador Independiente',
                'calidad_Trabajador dependiente sector privado',
                'calidad_Trabajador sector público afecto a la ley nº 18.834.',
                'calidad_Trabajador sector público no afecto a la ley nº 18.834.',
                'recencia_trabajador', 'frecuencia_trabajador_60D', 'frecuencia_trabajador_40D',
                'frecuencia_trabajador_20D', 'reposo_trabajador_60D', 'reposo_trabajador_40D',
                'reposo_trabajador_20D', 'n_medicos_distintos_xtrabajador_60D',
                'n_empleadores_distintos_xtrabajador_60D', 'desviacion_reposo_trabajador_60D',
                'recencia_medico', 'frecuencia_medico_30D', 'frecuencia_medico_15D',
                'frecuencia_medico_7D', 'reposo_medico_30D', 'reposo_medico_15D', 'reposo_medico_7D',
                'licencias_20_min', 'licencias_40_min', 'licencias_60_min', 'max_licencias_dia_30D',
                'frecuencia_J_30D_medico', 'frecuencia_F_30D_medico', 'frecuencia_M_30D_medico',
                'max_rest_days_30d', 'diferencia_dias', 'licencias_despues_umbral',
                'n_trabajadores_distintos_xmedico_60D', 'n_empleadores_distintos_xmedico_60D',
                'hhi_empleadores_por_medico_60D', 'n_remotas_30D', 'n_presenciales_30D',
                'recencia_empleador', 'frecuencia_empleador_60D', 'frecuencia_empleador_40D',
                'frecuencia_empleador_20D', 'reposo_empleador_60D', 'reposo_empleador_40D',
                'reposo_empleador_20D', 'n_trabajadores_distintos_xempleador_60D',
                'n_medicos_distintos_xempleador_60D', 'frecuencia_J_30D_empleador',
                'frecuencia_F_30D_empleador', 'frecuencia_M_30D_empleador',
                'historial_trabajador_medico', 'historial_empleador_medico', 'ponderado_medico_trabajador',
            ]

        self.feature_columns: List[str] = feature_columns
        self.scaler: MinMaxScaler = MinMaxScaler()
        self.model: IsolationForest = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=random_state,
        )
        self._is_fitted: bool = False

    def get_feature_names(self) -> List[str]:
        return list(self.feature_columns)

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        - Garantiza la presencia de todas las columnas requeridas (crea con 0 si faltan, útil para dummies)
        - Fuerza a numérico y reemplaza NaN/inf por 0
        - Devuelve un DataFrame X con el orden de columnas establecido
        """
        X = df.copy()
        for col in self.feature_columns:
            if col not in X.columns:
                X[col] = 0

        X = X[self.feature_columns]

        # Coerción a numérico y saneo
        for col in X.columns:
            X[col] = pd.to_numeric(X[col], errors='coerce')

        X = X.replace([np.inf, -np.inf], np.nan).fillna(0)
        return X

    @staticmethod
    def asignar_propensity_score_anomalias(
        df: pd.DataFrame,
        col_decision_function: str,
        col_propensity_score: str,
    ) -> pd.DataFrame:
        """
        Asigna un propensity score en [0,1] a partir de la función de decisión del modelo.
        - Valores >= 0 reciben 0 (no anómalos)
        - Valores < 0 se escalan linealmente usando el mínimo valor negativo observado
        """
        df_resultado = df.copy()

        if col_decision_function not in df_resultado.columns:
            raise ValueError(f"Columna '{col_decision_function}' no encontrada en DataFrame")

        valores = pd.to_numeric(df_resultado[col_decision_function], errors='coerce').fillna(0)
        negativos = valores[valores < 0]

        if len(negativos) == 0:
            df_resultado[col_propensity_score] = 0.0
            return df_resultado

        valor_min = negativos.min()

        def _scale(x: float) -> float:
            if x >= 0:
                return 0.0
            # Escala lineal a [0,1] tomando 0 como mejor (no anomalía) y valor_min como peor (más anómalo)
            return float((x - 0.0) / (valor_min - 0.0))

        df_resultado[col_propensity_score] = valores.apply(_scale)
        return df_resultado

    def fit(self, df_seleccion: pd.DataFrame) -> "AnomaliesModel":
        """Entrena el scaler y el IsolationForest con los datos proporcionados."""
        X = self._prepare_features(df_seleccion)
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self._is_fitted = True
        return self

    def transform(
        self,
        df_seleccion: pd.DataFrame,
        decision_col: str = 'anomaly_score',
        propensity_col: str = 'propensity_score_iforest',
    ) -> pd.DataFrame:
        """
        Aplica el modelo entrenado para obtener las columnas 'anomaly_score' y 'propensity_score_iforest'.
        """
        if not self._is_fitted:
            raise RuntimeError("El modelo no ha sido entrenado. Llama a fit() o fit_transform() primero.")

        X = self._prepare_features(df_seleccion)
        X_scaled = self.scaler.transform(X)
        decision_values = self.model.decision_function(X_scaled)

        df_out = df_seleccion.copy()
        df_out[decision_col] = decision_values
        df_out = self.asignar_propensity_score_anomalias(
            df=df_out,
            col_decision_function=decision_col,
            col_propensity_score=propensity_col,
        )
        return df_out

    def fit_transform(
        self,
        df_seleccion: pd.DataFrame,
        decision_col: str = 'anomaly_score',
        propensity_col: str = 'propensity_score_iforest',
    ) -> pd.DataFrame:
        """Conveniencia: entrena y luego transforma sobre el mismo DataFrame."""
        self.fit(df_seleccion)
        return self.transform(df_seleccion, decision_col=decision_col, propensity_col=propensity_col)

def calcular_anomalias(df_seleccion: pd.DataFrame):
    base_path = os.path.dirname(os.path.abspath(__file__)) + '/' 
    with open(f"{base_path}/modelo_anomalias.pkl", "rb") as f:
        modelo = pkl.load(f)
        df_resultados = modelo.fit_transform(df_seleccion)
        df_resultados.to_csv(f"{base_path}/resultados_anomalias.csv", index=False)