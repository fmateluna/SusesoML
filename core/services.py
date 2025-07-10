import datetime
from typing import List, Optional
from sqlalchemy import text, exc
from core.database import SessionLocal
#from models.consultas import Consulta1Response
import pandas as pd
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Tuple

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

def update_propensity_score_licencias(results: List[dict], score_column: str, rn:int) -> None:
    session = SessionLocal()
    try:
        df = pd.DataFrame(results)

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
            for _, row in df.iterrows()
        ]

        # Ejecutar el upsert en una transacción
        for params in params_list:
            session.execute(text(upsert_query), params)

        session.commit()
        print(f"Tabla ml.propensity_score = {params_list[0]}")

    except exc.SQLAlchemyError as e:
        session.rollback()
        raise ValueError(f"Error al actualizar ml.propensity_score: {str(e)}")
    except Exception as e:
        session.rollback()
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


