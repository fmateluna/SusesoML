
import pandas as pd
from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class ConsultaLicenciaRequest(BaseModel):
    id_lic: Optional[str] = None
    rut_trabajador: Optional[str] = None
    rut_medico: Optional[str] = None
    rut_empleador: Optional[str] = None
    folio: Optional[str] = None
    fecha: Optional[date] = None
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    cod_diagnostico: Optional[str] = None
    especialidad_medico: Optional[str] = None
    content_type: Optional[str]="csv"

class SemaforoRequest(BaseModel):
    mes: int
    anio: int
    sort_values_by: Optional[str] = "smf_rn"
    umbral_decorte: Optional[float] = 0.6
    rn_ln_mes: Optional[int] = 2
    umbral_deanomalias: Optional[float] = 0.5
    content_type: Optional[str] = "csv"

# Modelo para validar la entrada
class ConsultaRequest(BaseModel):
    especialidad_profesional: str
    cod_diagnostico_principal: str
    nombre_columna: str
    fecha_inicio: str
    fecha_fin: str
    
# Modelo para validar la entrada
class MasivoRequest(BaseModel):
    fecha_inicio: str
    fecha_fin: str    

class UmbralRequest(BaseModel):
    fecha: str
    dias: Optional[int] = 60
    columna_entidad: Optional[str] = "rut_medico"



class Consulta1Response(BaseModel):
    fecha_inicio: Optional[str]
    fecha_fin: Optional[str]
    folios_encontrados: Optional[List[str]] 
    
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

        df.loc[condiciones_especialidad & condiciones_diagnostico & condiciones_dias, nombre_columna] = 69
        return df

    def predict_prob(self, df):
        """
        Aplica preprocesamiento y luego la regla de negocio.
        """
        df = self.preprocess(df)
        df = self.apply_business_rule(df)
        return df

