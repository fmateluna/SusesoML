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