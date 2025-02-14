import datetime
from datetime import date, datetime
from typing import List, Optional
from sqlalchemy import text, exc
from core.database import SessionLocal
from models.consultas import Consulta1Response

def parse_dates(fecha_inicio: str, fecha_fin: str) -> tuple[date, date]:
    """Convierte las fechas de string a date, lanzando un error si el formato no es válido."""
    try:
        return (
            datetime.strptime(fecha_inicio, "%Y-%m-%d").date(),
            datetime.strptime(fecha_fin, "%Y-%m-%d").date(),
        )
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
        raise ValueError(f"Error en la ejecución de la consulta SQL: {str(e)}")
    except Exception as e:
        session.rollback()
        raise ValueError(f"Error inesperado: {str(e)}")
    finally:
        session.close()


def busca_datos_consulta1(folios: Optional[List[str]], fecha_inicio: str, fecha_fin: str) -> Consulta1Response:
    fecha_inicio, fecha_fin = parse_dates(fecha_inicio, fecha_fin)
    
    query_params = {
        "folio": folios, 
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
    }

    try:
        result = execute_query("./sql/consulta1.sql", query_params)
        if not result:
            return Consulta1Response(fecha_inicio=None, fecha_fin=None, folios_encontrados=[])

        fecha_inicio_result, fecha_fin_result = result[0]
        #folios_encontrados = [row["folio"] for row in result if row.get("folio")]

        return Consulta1Response(
            fecha_inicio=str(fecha_inicio_result) if fecha_inicio_result else None,
            fecha_fin=str(fecha_fin_result) if fecha_fin_result else None,
            folios_encontrados=folios
        )
    except Exception as e:
        print(f"Error ejecutando la consulta busca_datos_consulta1: {e}")
        raise

