from threading import Lock
import calendar
from datetime import date, datetime
from fastapi.encoders import jsonable_encoder
from core.anomalias import calcular_anomalias
from core.manager_score import ManagerPickle
from core.manager_umbral import process_umbral_data
from core.repo_umbrales.execute_umbrales import process_umbral_and_save_db
from core.semaforo import procesar_semaforo
from core.services import consulta_licencia, consulta_semaforo, manage_umbral_status, query_masivo,query_score_licencia,query_data_umbral
import logging
import os
import csv
from multiprocessing import  Queue
import pandas as pd
from models.consultas import ConsultaLicenciaRequest, SemaforoRequest

import pandas as pd
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi.responses import StreamingResponse
import io

umbral_cache = {}
cache_lock = Lock()



def manage_umbral_status_cache(
    request_hash: str,
    fecha: str,
    dias: int,
    entidad: str,
    status: str
) -> dict:
    """
    Inserta o actualiza el estado en el cache global y devuelve el registro.
    """
    record = {
        "status": status,
        "request_hash": request_hash,
        "fecha": fecha,
        "dias": dias,
        "entidad": entidad,
        "created_at": datetime.now().isoformat()
    }

    # Actualiza cache de manera segura
    with cache_lock:
        umbral_cache[request_hash] = record

    return record


def get_umbral_status_cache(request_hash: str) -> dict | None:
    """
    Recupera un registro desde el cache global.
    """
    with cache_lock:
        return umbral_cache.get(request_hash)

def to_csv_str(df):
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),  # iterador síncrono
        media_type="text/csv"
    )


def to_json(df: pd.DataFrame):
    data = df.fillna("").to_dict(orient="records")
    return JSONResponse(content=jsonable_encoder(data))

def to_csv(df: pd.DataFrame):
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=consulta.csv"}
    )


FORMAT_DISPATCHER = {
    "json": to_json,
    "csv": to_csv_str
}

execute_scores_map = {}
managerPickle =  ManagerPickle()

def masivo(fecha_inicio: str, fecha_fin: str):
    from_db = query_masivo(fecha_inicio, fecha_fin)
    if from_db.empty:
        return []
    result = managerPickle.ejecuta_masivo(from_db, fecha_inicio, fecha_fin)
    return result

def propensy_score(fecha_inicio: str, fecha_fin: str):
    key = makeKeyFromFechas(fecha_inicio, fecha_fin)

    # Consulta si l ejecucion masiva ya se realizo por los parametros de fechas del request
    if len(execute_scores_map) == 0 or execute_scores_map.get(key) is None:        
        execute_scores_map[key] = "run"
        return managerPickle.ejecuta_masivo( fecha_inicio, fecha_fin)
    return managerPickle.consulta_ejecuta_masivo(fecha_inicio, fecha_fin)

def propensy_score_licencia(fecha_inicio: str, fecha_fin: str):
    from_db = query_score_licencia(fecha_inicio, fecha_fin)
    return from_db

def generate_data_umbral(fecha: str, dias: int = 60, columna_entidad: str = "rut_medico"):
    data = query_data_umbral(fecha, dias, columna_entidad)
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data, columns=[
        "id_licencia",
        "folio",
        "dias_reposo",
        "fecha_emision",
        "fecha_inicio_reposo",
        "especialidad_profesional",
        "cod_diagnostico_principal",
        "rut_medico",
        "rut_trabajador",
        "calidad_trabajador",
        "rut_empleador",
        "marca_otorgamiento",
        "edad_trabajador",
        "sexo_trabajador",        
        "n_trabajadores"
    ])
    processed_df = process_umbral_data(df, entity_col=columna_entidad)
    return processed_df

def makeKeyFromFechas(fecha_inicio: str, fecha_fin: str):
    """
    Genera una clave única basada en fecha_inicio y fecha_fin.
    """
    return f"{fecha_inicio}_{fecha_fin}"    


def save_to_csv(df: pd.DataFrame, output_path: str) -> None:
    """Save DataFrame to a CSV file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if df.empty:
        logger.warning(f"No existen resultado {output_path}")
        return
    df.to_csv(output_path, index=False, encoding='utf-8')
    logger.info(f"CSV guardado {output_path}")
    

def consulta_licencia_from_rest(where_query: ConsultaLicenciaRequest):
    df = consulta_licencia(where_query)  
    content_type = getattr(where_query, "content_type", "json").lower()
    converter = FORMAT_DISPATCHER.get(content_type, to_json)

    return converter(df)


def process_umbral_task(fecha: str, dias: int, columna_entidad: str, request_hash: str, status_queue: Queue) -> None:

    try:

        status_queue.put(
            manage_umbral_status(
                request_hash=request_hash,
                fecha=fecha,
                dias=dias,
                entidad=columna_entidad,
                status="extract_data"
            )
        )
        # Ejecutar consulta y procesar datos
        data_df = generate_data_umbral(fecha, dias, columna_entidad)

        status_queue.put(
            manage_umbral_status(
                request_hash=request_hash,
                fecha=fecha,
                dias=dias,
                entidad=columna_entidad,
                status="process_data"
            )
        )

        process_umbral_and_save_db(data_df,dias,columna_entidad)        

        status_queue.put(
            manage_umbral_status(
                request_hash=request_hash,
                fecha=fecha,
                dias=dias,
                entidad=columna_entidad,
                status="calc_data_anomaly"
            )
        )
        calcular_anomalias(data_df)
        # Registrar estado final
        status_queue.put(
            manage_umbral_status(
                request_hash=request_hash,
                fecha=fecha,
                dias=dias,
                entidad=columna_entidad,
                status="finish"
            )
        )
    except Exception as e:
        status_queue.put(
            manage_umbral_status(
                request_hash=request_hash,
                fecha=fecha,
                dias=dias,
                entidad=columna_entidad,
                status="error"
            )
        )

def consulta_semaforo_from_rest(request: SemaforoRequest):
    fecha_inicio, fecha_fin = None, None

    if request.mes and request.anio:
        fecha_inicio = date(request.anio, request.mes, 1).isoformat()
        last_day = calendar.monthrange(request.anio, request.mes)[1]
        fecha_fin = date(request.anio, request.mes, last_day).isoformat()

    where_query = ConsultaLicenciaRequest(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        rut_medico=request.rut_medico,
        content_type=request.content_type
    )

    df_calculos = consulta_licencia(where_query)
    return df_calculos

def consulta_rest_semaforo(rango: str, rut_medico: str):
    from_db =consulta_semaforo(rango, rut_medico)
    return from_db