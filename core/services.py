import datetime
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text, exc
from core.database import SessionLocal
import pandas as pd
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Tuple
import logging
from collections import defaultdict
from datetime import datetime
import time

from sqlalchemy import text
from datetime import datetime

from dataclasses import dataclass
from typing import Optional
from datetime import date

from models.consultas import ConsultaLicenciaRequest




logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_dates(fecha_inicio: str, fecha_fin: str) -> Tuple[datetime, datetime]:
    """
    Convierte las fechas de string a datetime con rango completo de día.

    - inicio: YYYY-MM-DD 00:00:00
    - fin: YYYY-MM-DD 23:59:59.999999

    Lanza un ValueError si el formato no es válido.
    """
    try:
        fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d") + timedelta(days=1) - timedelta(microseconds=1)

        return fecha_inicio_dt, fecha_fin_dt
    except ValueError:
        raise ValueError("Las fechas deben estar en formato YYYY-MM-DD")



def read_sql_file(file_path: str) -> str:
    """Lee una consulta SQL desde un archivo y la devuelve como un string."""
    with open(file_path, "r") as file:
        return file.read()


def execute_query(file_path: str, params: dict):
    """Ejecuta una consulta SQL desde un archivo con parámetros proporcionados."""
    session = SessionLocal()
    query = read_sql_file(file_path)
    try:
        result = session.execute(text(query), params).fetchall()
        return result
    except exc.SQLAlchemyError as e:
        session.rollback()
        raise ValueError(f"Error en la ejecución de la consulta SQL: {str(e)}") from exc.SQLAlchemyError
    except Exception as e:
        session.rollback()
        raise ValueError(f"Error inesperado: {str(e)}") from Exception
    finally:
        session.close()


def query_regla_negocio(
    cod_diagnostico_principal, especialidad_profesional, fecha_inicio, fecha_fin: str
) -> pd.DataFrame:
    fecha_inicio_date, fecha_fin_date = parse_dates(fecha_inicio, fecha_fin)

    query_params = {
        "cod_diagnostico_principal": cod_diagnostico_principal,
        "especialidad_profesional": especialidad_profesional,
        "fecha_inicio": fecha_inicio_date,
        "fecha_fin": fecha_fin_date,
    }

    try:
        result = execute_query("./sql/consulta1.sql", query_params)

        if not result:
            return pd.DataFrame() 
        df = pd.DataFrame(result, columns=[
            "id_licencia",
            "folio",
            "dias_reposo",
            "fecha_emision",
            "fecha_inicio_reposo",
            "especialidad_profesional",
            "cod_diagnostico_principal"
        ])

        return df

    except Exception as e:
        print(f"Error ejecutando la consulta busca_datos_consulta1: {e}")
        raise

def update_propensity_score_licencias(results: pd.DataFrame, score_column: str, rn: int):
    """
    Actualiza la tabla ml.propensity_score con un lote de resultados.
    """
    session = SessionLocal()
    try:
        if results.empty or score_column not in results.columns:
            logger.error(f"Datos vacíos o columna {score_column} no encontrada")
            return

        upsert_query = """
        INSERT INTO ml.propensity_score (id_lic, folio, rn, score)
        VALUES (:id_lic, :folio, :rn, :score)
        ON CONFLICT (id_lic, rn) DO UPDATE
        SET score = EXCLUDED.score
        """
        params_list = [
            {
                'id_lic': row['id_licencia'],
                'folio': row['folio'],
                'rn': rn,
                'score': row[score_column]
            }
            for _, row in results.iterrows()
        ]
        #logger.info(f"Insertando {len(params_list)} registros en ml.propensity_score")
        session.execute(text(upsert_query), params_list)
        session.commit()
        successful_ids = [row['id_licencia'] for _, row in results.iterrows()]
        logger.info(f"Registros insertados exitosamente: {successful_ids}")
    except SQLAlchemyError as e: 
        session.rollback()
        logger.error(f"Error al actualizar ml.propensity_score: {str(e)}")
        raise ValueError(f"Error al actualizar ml.propensity_score: {str(e)}")
    except Exception as e:
        session.rollback()
        logger.error(f"Error inesperado al actualizar ml.propensity_score: {str(e)}")
        raise ValueError(f"Error inesperado al actualizar ml.propensity_score: {str(e)}")
    finally:
        session.close()
        
def query_masivo(
     fecha_inicio, fecha_fin: str
) -> pd.DataFrame:
    fecha_inicio_date, fecha_fin_date = parse_dates(fecha_inicio, fecha_fin)

    query_params = {
        "fecha_inicio": fecha_inicio_date,
        "fecha_fin": fecha_fin_date,
    }

    try:
        result = execute_query("./sql/masivo.sql", query_params)

        if not result:
            return pd.DataFrame() 
        df = pd.DataFrame(result, columns=[
            "id_licencia",
            "folio",
            "dias_reposo",
            "fecha_emision",
            "fecha_inicio_reposo",
            "especialidad_profesional",
            "cod_diagnostico_principal"
        ])

        return df

    except Exception as e:
        print(f"Error ejecutando la consulta busca_datos_consulta1: {e}")
        raise        
    
    
def query_score(fecha_inicio, fecha_fin: str)-> dict:
    fecha_inicio_date, fecha_fin_date = parse_dates(fecha_inicio, fecha_fin)


    query_params = {
        "fecha_inicio": fecha_inicio_date,
        "fecha_fin": fecha_fin_date,
    }

    result = execute_query("./sql/propensy_score_resume.sql", query_params)

    if not result:
        return []

    data = [
        {
            "fecha_emision": row[0],
            "rn": row[1],
            "cantidad_registros": row[2]
        }
        for row in result
    ]
    return data



def query_score_licencia(fecha_inicio: str, fecha_fin: str) -> list[dict]:
    fecha_inicio_date, fecha_fin_date = parse_dates(fecha_inicio, fecha_fin)

    query_params = {
        "fecha_inicio": fecha_inicio_date,
        "fecha_fin": fecha_fin_date,
    }

    result = execute_query("./sql/propensy_score_licencia.sql", query_params)

    if not result:
        return []

    agrupados = defaultdict(lambda: {"score": {}})

    for row in result:
        licencia = row[0]
        fecha_emision = row[1]
        rut_medico = row[2]
        dias_reposo = row[3]
        cod_diagnostico = row[4]
        especialidad_medico = row[5]
        rn = row[6]
        score = row[7]

        key = (licencia, fecha_emision, rut_medico, dias_reposo, cod_diagnostico, especialidad_medico)
        
        agrupados[key]["score"][f"rn_{rn}"] = score
        if "licencia" not in agrupados[key]:
            agrupados[key].update({
                "licencia": licencia,
                "fecha_emision": fecha_emision,
                "rut_medico": rut_medico,
                "dias_reposo": dias_reposo,
                "cod_diagnostico": cod_diagnostico,
                "especialidad_medico": especialidad_medico,
            })

    return list(agrupados.values())




def query_data_umbral(fecha: str, dias: int = 60, columna_entidad: str = "rut_medico") -> list:
    """Execute the SQL query and return results."""
    try:
        fecha_date = datetime.strptime(fecha, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("El formato de la fecha debe ser YYYY-MM-DD")

    query_params = {
        "fecha_inicio": fecha_date,
        "windows_days": dias,
    }

    # Simulate long-running query (replace with actual execute_query call)
    start_time = time.time()
    result = execute_query("./sql/datos_umbral.sql", query_params)
    execution_time = time.time() - start_time

    return result, execution_time


def manage_umbral_status(
    request_hash: str,
    fecha: str,
    dias: int,
    entidad: str,
    status: str,
    execution_time: float = None,
    message: str = None
) -> dict:
    """
    Inserta o actualiza el estado en la tabla ml.umbral_data y devuelve el registro.
    """
    session = SessionLocal()
    try:
        upsert_query = """
        INSERT INTO ml.umbral_data (hash, fecha, dias, entidad, estado, created_at)
        VALUES (:hash, :fecha, :dias, :entidad, :estado, :created_at)
        ON CONFLICT (hash) DO UPDATE
        SET estado = EXCLUDED.estado,
            created_at = EXCLUDED.created_at
        RETURNING hash, fecha, dias, entidad, estado, created_at
        """
        params = {
            "hash": request_hash,
            "fecha": fecha,
            "dias": dias,
            "entidad": entidad,
            "estado": status,
            "created_at": datetime.now()
        }
        result = session.execute(text(upsert_query), params).fetchone()
        session.commit()

        if not result:
            raise ValueError("No se pudo registrar o actualizar el estado en ml.umbral_data")

        # Construir el diccionario de respuesta
        status_data = {
            "status": result.estado,
            "request_hash": result.hash,
            "fecha": result.fecha,
            "dias": result.dias,
            "entidad": result.entidad,
            "created_at": result.created_at.isoformat()
        }

        return status_data

    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Error al gestionar estado en ml.umbral_data: {str(e)}")
        raise ValueError(f"Error al gestionar estado: {str(e)}")
    finally:
        session.close()

def get_umbral_status(request_hash: str) -> dict:
    """
    Consulta el estado de un request_hash en la tabla ml.umbral_data.
    """
    session = SessionLocal()
    try:
        query = """
        SELECT hash, fecha, dias, entidad, estado, created_at
        FROM ml.umbral_data
        WHERE hash = :hash
        """
        result = session.execute(text(query), {"hash": request_hash}).fetchone()
        if not result:
            return {"status": "not_found", "message": "Request hash not found"}

        return {
            "status": result.estado,
            "request_hash": result.hash,
            "fecha": result.fecha,
            "dias": result.dias,
            "entidad": result.entidad,
            "created_at": result.created_at.isoformat()
        }
    except SQLAlchemyError as e:
        logger.error(f"Error al consultar estado en ml.umbral_data: {str(e)}")
        raise ValueError(f"Error al consultar estado: {str(e)}")
    finally:
        session.close()


def insert_umbrales(results: pd.DataFrame, fecha: str, dias: int, columna_entidad: str):
    """
    Inserta los datos procesados de umbrales en la tabla umbrales.
    Asume que el DataFrame 'results' contiene las columnas necesarias después del procesamiento.
    Agrega las columnas fecha, dias y columna_entidad como valores constantes del request.
    Usa INSERT con ON CONFLICT DO UPDATE para manejar posibles duplicados (asumiendo unique constraint en id_lic, fecha).
    """
    session = SessionLocal()
    try:
        if results.empty:
            logger.warning("DataFrame vacío, no se insertan datos en umbrales")
            return

        # Agregar columnas constantes del request al DataFrame
        results['fecha'] = fecha
        results['dias'] = dias
        results['columna_entidad'] = columna_entidad

        if 'id_licencia' in results.columns:
            results = results.rename(columns={'id_licencia': 'id_lic'})

        expected_columns = [
            'id_lic', 'folio', 'fecha', 'dias', 'columna_entidad',
            'dias_reposo', 'fecha_emision', 'fecha_inicio_reposo',
            'especialidad_profesional', 'cod_diagnostico_principal',
            'rut_medico', 'rut_trabajador', 'marca_otorgamiento',
            'frecuencia_medico_30D', 'frecuencia_medico_15D', 'frecuencia_medico_7D',
            'frecuencia_J_30D_medico', 'frecuencia_F_30D_medico', 'frecuencia_M_30D_medico',
            'n_remotas_30D', 'n_presenciales_30D',
            'score_frecuencia_medico_7D', 'score_frecuencia_medico_15D',
            'score_frecuencia_medico_30D', 'score_frecuencia_F_30D_medico',
            'score_frecuencia_J_30D_medico', 'score_frecuencia_M_30D_medico',
            'score_n_remotas_30D', 'score_n_presenciales_30D'
        ]

        for col in expected_columns:
            if col not in results.columns:
                if 'score_' in col:
                    results[col] = 0.0
                else:
                    logger.warning(f"Columna {col} no encontrada en DataFrame, se omitirá o seteará a NULL")

        upsert_query = """
        INSERT INTO ml.umbrales (
            id_lic, folio, fecha, dias, columna_entidad,
            dias_reposo, fecha_emision, fecha_inicio_reposo,
            especialidad_profesional, cod_diagnostico_principal,
            rut_medico, rut_trabajador, marca_otorgamiento,
            frecuencia_medico_30D, frecuencia_medico_15D, frecuencia_medico_7D,
            frecuencia_J_30D_medico, frecuencia_F_30D_medico, frecuencia_M_30D_medico,
            n_remotas_30D, n_presenciales_30D,
            score_frecuencia_medico_7D, score_frecuencia_medico_15D,
            score_frecuencia_medico_30D, score_frecuencia_F_30D_medico,
            score_frecuencia_J_30D_medico, score_frecuencia_M_30D_medico,
            score_n_remotas_30D, score_n_presenciales_30D
        ) VALUES (
            :id_lic, :folio, :fecha, :dias, :columna_entidad,
            :dias_reposo, :fecha_emision, :fecha_inicio_reposo,
            :especialidad_profesional, :cod_diagnostico_principal,
            :rut_medico, :rut_trabajador, :marca_otorgamiento,
            :frecuencia_medico_30D, :frecuencia_medico_15D, :frecuencia_medico_7D,
            :frecuencia_J_30D_medico, :frecuencia_F_30D_medico, :frecuencia_M_30D_medico,
            :n_remotas_30D, :n_presenciales_30D,
            :score_frecuencia_medico_7D, :score_frecuencia_medico_15D,
            :score_frecuencia_medico_30D, :score_frecuencia_F_30D_medico,
            :score_frecuencia_J_30D_medico, :score_frecuencia_M_30D_medico,
            :score_n_remotas_30D, :score_n_presenciales_30D
        )
         ON CONFLICT (id_lic, dias, columna_entidad) DO NOTHING;
        """

        params_list = [
            {col: row.get(col, None) for col in expected_columns}
            for _, row in results.iterrows()
        ]

        session.execute(text(upsert_query), params_list)
        session.commit()
        logger.info(f"Insertados/actualizados {len(params_list)} registros en umbrales")

    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Error al insertar en umbrales: {str(e)}")
        raise ValueError(f"Error al insertar en umbrales: {str(e)}")
    except Exception as e:
        session.rollback()
        logger.error(f"Error inesperado al insertar en umbrales: {str(e)}")
        raise ValueError(f"Error inesperado al insertar en umbrales: {str(e)}")
    finally:
        session.close()        

def insert_anomalias(results: pd.DataFrame):
    """
    Inserta los datos procesados de anomalías en la tabla ml.anomalias.
    Usa INSERT con ON CONFLICT DO UPDATE para manejar duplicados (basado en id_lic).
    Se espera que 'results' tenga las columnas necesarias para la tabla ml.anomalias.
    """
    session = SessionLocal()
    try:
        if results.empty:
            logger.warning("DataFrame vacío, no se insertan datos en ml.anomalias")
            return

        # Renombrar si hace falta (consistencia)
        if 'id_licencia' in results.columns:
            results = results.rename(columns={'id_licencia': 'id_lic'})

        # Columnas que debe tener el DataFrame (idénticas a la tabla)
        expected_columns = [
            "id_lic", "rut_medico", "rut_trabajador", "rut_empleador",
            "dias_reposo", "edad_trabajador", "hora_emision", "dia_codificado",
            "calidad_trabajador_independiente", "calidad_trabajador_dependiente_privado",
            "calidad_trabajador_publico_afecto", "calidad_trabajador_publico_no_afecto",
            "recencia_trabajador", "frecuencia_trabajador_60d", "frecuencia_trabajador_40d",
            "frecuencia_trabajador_20d", "reposo_trabajador_60d", "reposo_trabajador_40d",
            "reposo_trabajador_20d", "n_medicos_distintos_xtrabajador_60d",
            "n_empleadores_distintos_xtrabajador_60d", "desviacion_reposo_trabajador_60d",
            "recencia_medico", "frecuencia_medico_30d", "frecuencia_medico_15d",
            "frecuencia_medico_7d", "reposo_medico_30d", "reposo_medico_15d",
            "reposo_medico_7d", "licencias_20_min", "licencias_40_min", "licencias_60_min",
            "max_licencias_dia_30d", "frecuencia_j_30d_medico", "frecuencia_f_30d_medico",
            "frecuencia_m_30d_medico", "max_rest_days_30d", "diferencia_dias",
            "licencias_despues_umbral", "n_trabajadores_distintos_xmedico_60d",
            "n_empleadores_distintos_xmedico_60d", "hhi_empleadores_por_medico_60d",
            "n_remotas_30d", "n_presenciales_30d", "recencia_empleador",
            "frecuencia_empleador_60d", "frecuencia_empleador_40d", "frecuencia_empleador_20d",
            "reposo_empleador_60d", "reposo_empleador_40d", "reposo_empleador_20d",
            "n_trabajadores_distintos_xempleador_60d", "n_medicos_distintos_xempleador_60d",
            "frecuencia_j_30d_empleador", "frecuencia_f_30d_empleador", "frecuencia_m_30d_empleador",
            "historial_trabajador_medico", "historial_empleador_medico", "ponderado_medico_trabajador",
            "anomaly_score", "propensity_score_iforest"
        ]

        # Asegurar que el DF tenga todas las columnas (si falta alguna → None)
        for col in expected_columns:
            if col not in results.columns:
                results[col] = None

        upsert_query = f"""
        INSERT INTO ml.anomalias (
            {", ".join(expected_columns)}
        ) VALUES (
            {", ".join([f":{col}" for col in expected_columns])}
        )
        ON CONFLICT (id_lic) DO UPDATE
        SET
            {", ".join([f"{col} = EXCLUDED.{col}" for col in expected_columns if col != "id_lic"])}
        ;
        """

        params_list = [
            {col: row.get(col, None) for col in expected_columns}
            for _, row in results.iterrows()
        ]

        session.execute(text(upsert_query), params_list)
        session.commit()
        logger.info(f"Insertados/actualizados {len(params_list)} registros en ml.anomalias")

    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Error al insertar en ml.anomalias: {str(e)}")
        raise ValueError(f"Error al insertar en ml.anomalias: {str(e)}")
    except Exception as e:
        session.rollback()
        logger.error(f"Error inesperado al insertar en ml.anomalias: {str(e)}")
        raise ValueError(f"Error inesperado al insertar en ml.anomalias: {str(e)}")
    finally:
        session.close()

def consulta_licencia(where_query: ConsultaLicenciaRequest) -> pd.DataFrame:
    """
    Ejecuta la consulta de licencias con filtros opcionales.
    """
    query_path = "./sql/consulta_licencia.sql"

    # Si tiene fecha única → ignoramos rango
    fecha_unica = where_query.fecha
    fecha_inicio = where_query.fecha_inicio
    fecha_fin = where_query.fecha_fin

    

    # Si viene rango incompleto, lo ignoramos
    if (fecha_inicio and not fecha_fin) or (fecha_fin and not fecha_inicio):
        raise ValueError("Debe especificar tanto fecha_inicio como fecha_fin o ninguna")
    else:
         if (fecha_inicio and fecha_fin):
            fecha_inicio, fecha_fin = parse_dates(where_query.fecha_inicio, where_query.fecha_fin)

    query_params = {
        "id_lic": where_query.id_lic,
        "rut_trabajador": where_query.rut_trabajador,
        "rut_medico": where_query.rut_medico,
        "rut_empleador": where_query.rut_empleador,
        "folio": where_query.folio,
        "fecha_unica": fecha_unica,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "cod_diagnostico": where_query.cod_diagnostico,
        "especialidad_medico": where_query.especialidad_medico,
    }

    try:
        result = execute_query(query_path, query_params)

        if not result:
            return pd.DataFrame()
        
        df = pd.DataFrame(result, columns=[
            "id_lic", "operador", "ccaf", "entidad_pagadora", "folio",
            "fecha_emision", "empleador_adscrito", "codigo_interno_prestador",
            "comuna_prestador", "fecha_ultimo_estado", "ultimo_estado",
            "rut_trabajador", "sexo_trabajador", "edad_trabajador",
            "tipo_reposo", "dias_reposo", "fecha_inicio_reposo",
            "comuna_reposo", "tipo_licencia", "rut_medico",
            "tipo_licencia_pronunciamiento", "codigo_continuacion_pronunciamiento",
            "dias_autorizados_pronunciamiento", "codigo_diagnostico_pronunciamiento",
            "codigo_autorizacion_pronunciamiento", "causa_rechazo_pronunciamiento",
            "tipo_reposo_pronunciamiento", "derecho_a_subsidio_pronunciamiento",
            "rut_empleador", "calidad_trabajador", "actividad_laboral_trabajador",
            "ocupacion", "entidad_pagadora_zona_c", "fecha_recepcion_empleador",
            "regimen_previsional", "entidad_pagadora_subsidio", "comuna_laboral",
            "comuna_uso_compin", "cantidad_de_pronunciamientos", "cantidad_de_zonas_d",
            "secuencia_estados", "cod_diagnostico_principal", "cod_diagnostico_secundario",
            "periodo", "marca_otorgamiento", "cod_diagnostico", "especialidad_medico",
            "rn1", "rn2", "score_frecuencia_medico_7d", "score_frecuencia_medico_15d",
            "score_frecuencia_medico_30d", "score_frecuencia_f_30d_medico",
            "score_frecuencia_j_30d_medico", "score_frecuencia_m_30d_medico",
            "score_n_remotas_30d", "score_n_presenciales_30d"
        ])
        return df

    except Exception as e:
        logger.error(f"Error ejecutando consulta_licencia: {e}")
        raise
