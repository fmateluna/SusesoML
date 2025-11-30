import pandas as pd
import numpy as np
import logging
from typing import Optional
import os
from core.services import guardar_semaforo
# from core.utils.custom_logger import get_custom_logger

# Configura el logger personalizado para semáforo
# semaforo_logger = get_custom_logger('semaforo_logger', 'semaforo.log')
semaforo_logger = logging.getLogger('semaforo_logger')

class SemaforoWatson:
  """
  Calcula indicadores 'semáforo' por médico combinando reglas, umbrales y anomalías.
  Permite configurar valores por defecto y sobreescribirlos por llamada.

  --- Ejemplo de uso
  sw = SemaforoWatson(sort_values_by=“smf_rn”, umbral_decorte=0.6, rn_ln_mes=400)
  resultado = sw.compute(df_to_semaforo, mes=7, anio=2025) (edited)
  """
  REQUIRED_COLUMNS = {
      "rut_medico",
      "fecha_emision",
      "propensity_score_rn",
      "propensity_score_umbrales",
      "propensity_score_iforest",
      }

  def __init__(
      self,
      *,
      sort_values_by: str = "um",
      umbral_decorte: float = 0.5,
      rn_ln_mes: int = 400,
      umbral_deanomalias: float = 0.5,
      ) -> None:
      self.sort_values_by = sort_values_by
      # - Propensity_score_rn es 0 si ningun rn es 1 y es 1 si al menos 1 rn es  1. 
      # - Propensity_score_umbrales es el maximo score de umbrales de todos los scores de umbrales para una licencia      
      self.umbral_decorte = umbral_decorte
      self.rn_ln_mes = rn_ln_mes
      self.umbral_deanomalias = umbral_deanomalias

  def compute(
      self,
      dataframe: pd.DataFrame,
      *,
      mes: Optional[int] = None,
      anio: Optional[int] = None,
      show_results: Optional[int] = None,
      sort_values_by: Optional[str] = None,
      umbral_decorte: Optional[float] = None,
      rn_ln_mes: Optional[int] = None,
      umbral_deanomalias: Optional[float] = None,
  ) -> pd.DataFrame:
      """
      Ejecuta el cálculo de semáforos por médico.
      """
      
      # Convierte las columnas a numérico, forzando errores a NaN
      dataframe["rn1"] = pd.to_numeric(dataframe["rn1"], errors="coerce").fillna(0).astype(int)
      dataframe["rn2"] = pd.to_numeric(dataframe["rn2"], errors="coerce").fillna(0).astype(int)

      # Asigna propensity_score_rn usando np.where
      dataframe["propensity_score_rn"] = np.where(dataframe["rn1"] + dataframe["rn2"] == 0, 0, 1)

      # Propensity_score_umbrales es el máximo score de umbrales
      score_columns = [
          "score_frecuencia_medico_7d",
          "score_frecuencia_medico_15d",
          "score_frecuencia_medico_30d",
          "score_frecuencia_f_30d_medico",
          "score_frecuencia_j_30d_medico",
          "score_frecuencia_m_30d_medico",
          "score_n_remotas_30d",
          "score_n_presenciales_30d"
      ]

      for col in score_columns:
          dataframe[col] = pd.to_numeric(dataframe[col], errors="coerce").fillna(0)
      dataframe["propensity_score_umbrales"] = dataframe[score_columns].max(axis=1)        

      dataframe["propensity_score_iforest"] = dataframe["anomalias_propensity_score_iforest"]

      sort_by = sort_values_by if sort_values_by is not None else self.sort_values_by
      u_corte = umbral_decorte if umbral_decorte is not None else self.umbral_decorte
      rn_lim = rn_ln_mes if rn_ln_mes is not None else self.rn_ln_mes
      u_anom = umbral_deanomalias if umbral_deanomalias is not None else self.umbral_deanomalias

      missing = self.REQUIRED_COLUMNS - set(dataframe.columns)
      df = dataframe.copy()
      if missing:
        raise ValueError(f"Faltan columnas requeridas: {sorted(missing)}")

      
      df["fecha_emision"] = pd.to_datetime(df["fecha_emision"], errors="coerce")

      if mes is not None:
        df = df[df["fecha_emision"].dt.month == mes]

      if anio is not None:
        df = df[df["fecha_emision"].dt.year == anio]

      umbrales_df = (
          df[df["propensity_score_umbrales"] >= u_corte]
          .groupby("rut_medico")
          .size()
          .reset_index(name="um")
          )

      anomalias_df = (
          df[df["propensity_score_iforest"] >= u_anom]
          .groupby("rut_medico")
          .size()
          .reset_index(name="an")
          )

      semaforo_watson = (
          df.groupby("rut_medico")
          .agg(
              n_lic=("rut_medico", "count"),
              rn=("propensity_score_rn", "sum"),
              )
          .reset_index()
          .sort_values(by="n_lic", ascending=False)
          )
      
      semaforo_watson["rango"]=f"{anio}-{mes:02d}"

      semaforo_watson = semaforo_watson.merge(umbrales_df, on="rut_medico", how="left")
      semaforo_watson = semaforo_watson.merge(anomalias_df, on="rut_medico", how="left")
      semaforo_watson["um"] = semaforo_watson["um"].fillna(0).astype(int)
      semaforo_watson["an"] = semaforo_watson["an"].fillna(0).astype(int)
      semaforo_watson["smf_rn"] = semaforo_watson.apply(
          lambda row: 1 if row["n_lic"] >= rn_lim else (row["rn"] / row["n_lic"] if row["n_lic"] > 0 else 0),
          axis=1,
          )
      den_um = semaforo_watson["n_lic"] - semaforo_watson["rn"]
      den_an = semaforo_watson["n_lic"] - semaforo_watson["rn"] - semaforo_watson["um"]
      semaforo_watson["smf_um"] = np.where(den_um > 0, semaforo_watson["um"] / den_um, 0.0)
      semaforo_watson["smf_an"] = np.where(den_an > 0, semaforo_watson["an"] / den_an, 0.0)

      if sort_by in semaforo_watson.columns:
        semaforo_watson = semaforo_watson.sort_values(by=sort_by, ascending=False)

      for col in semaforo_watson.select_dtypes(include=["float"]).columns:
        col_vals = semaforo_watson[col]
        if np.all(np.isfinite(col_vals)) and np.all(np.mod(col_vals, 1) == 0):
          semaforo_watson[col] = col_vals.astype("Int64")

      # Guardado en base de datos
      num_registros_a_guardar = len(semaforo_watson)
      semaforo_logger.info(f"Inicia el guardado de {num_registros_a_guardar} registros de semáforo en la base de datos.")
      for _, row in semaforo_watson.iterrows():
          guardar_semaforo(row)
      semaforo_logger.info(f"Finaliza el guardado de registros de semáforo.")


      if show_results is not None:
        return semaforo_watson.head(show_results)

      return semaforo_watson

  @staticmethod
  def semaforoWatson(
      dataframe: pd.DataFrame,
      mes: Optional[int] = None,
      anio: Optional[int] = None,
      show_results: Optional[int] = None,
      sort_values_by: str = "um",
      umbral_decorte: float = 0.5,
      rn_ln_mes: int = 400,
      umbral_deanomalias: float = 0.5,
      ) -> pd.DataFrame:
      """
      Mantiene la firma original como método estático, delegando en compute.
      """

      return SemaforoWatson(
          sort_values_by=sort_values_by,
          umbral_decorte=umbral_decorte,
          rn_ln_mes=rn_ln_mes,
          umbral_deanomalias=umbral_deanomalias,
          ).compute(
              dataframe,
              mes=mes,
              anio=anio,
              show_results=show_results,
              )
  
def procesar_semaforo(
    df_calculos: pd.DataFrame,
    mes: int = 8,
    anio: int = 2025,
    sort_values_by: str = "smf_rn",
    umbral_decorte: float = 0.6,
    rn_ln_mes: int = 2,
    umbral_deanomalias: float = 0.5
) -> pd.DataFrame:
    """
    Procesa un DataFrame con datos médicos y devuelve los resultados de SemaforoWatson para todas las filas.
    """
    parametros_str = f"mes={mes}, anio={anio}, sort_by='{sort_values_by}', umbral_corte={umbral_decorte}, rn_limite={rn_ln_mes}, umbral_anomalias={umbral_deanomalias}"
    semaforo_logger.info(f"Inicia procesamiento de semáforo con {len(df_calculos)} registros. Parámetros: {parametros_str}.")
    
    df_calculos["fecha_emision"] = pd.to_datetime(df_calculos["fecha_emision"], errors="coerce")
    
    total_filas = len(df_calculos)
    semaforo_logger.info(f"total lineas calculadas  {total_filas} registros. Parámetros: {parametros_str}.")
    sw = SemaforoWatson(
        sort_values_by=sort_values_by,
        umbral_decorte=umbral_decorte,
        rn_ln_mes=rn_ln_mes,
        umbral_deanomalias=umbral_deanomalias
    )
    
    # Ejecutar el cálculo
    resultado = sw.compute(
        df_calculos,
        mes=mes,
        anio=anio,
        show_results=total_filas,
        sort_values_by=sort_values_by,
        umbral_decorte=umbral_decorte,
        rn_ln_mes=rn_ln_mes,
        umbral_deanomalias=umbral_deanomalias
    )
    
    # Agregar la columna "rango" con el formato "anio-mes", para identificar el rango del semaforo
    if anio is not None and mes is not None:
        resultado["rango"] = f"{anio}-{mes:02d}"
    
    semaforo_logger.info(f"Finaliza procesamiento de semáforo. Se generaron {len(resultado)} resultados.")
    return resultado
