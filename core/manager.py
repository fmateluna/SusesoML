
from core.anomalias import calcular_anomalias
from core.manager_score import ManagerPickle
from core.manager_umbral import process_umbral_data
from core.repo_umbrales.execute_umbrales import csv_to_results_umbrales
from core.services import query_masivo,query_score_licencia,query_data_umbral
import logging
import os
import csv
from multiprocessing import  Queue
import pandas as pd
from core.services import query_data_umbral, manage_umbral_status
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    data, execution_time = query_data_umbral(fecha, dias, columna_entidad)
    if not data:
        return pd.DataFrame(), execution_time
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
        "marca_otorgamiento"
    ])
    processed_df = process_umbral_data(df, entity_col=columna_entidad)
    return processed_df, execution_time

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

def process_umbral_task(fecha: str, dias: int, columna_entidad: str, request_hash: str, status_queue: Queue) -> None:
    """Process the umbral query, apply calculations, and save results to CSV."""
    try:
        # Registrar estado inicial
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
        data_df, execution_time = generate_data_umbral(fecha, dias, columna_entidad)
        status_queue.put(
            manage_umbral_status(
                request_hash=request_hash,
                fecha=fecha,
                dias=dias,
                entidad=columna_entidad,
                status="extract_data",
                execution_time=execution_time
            )
        )

        # Guardar resultados en CSV
        status_queue.put(
            manage_umbral_status(
                request_hash=request_hash,
                fecha=fecha,
                dias=dias,
                entidad=columna_entidad,
                status="process_data"
            )
        )
        data_csv_path = f"./umbrales_csv/{fecha}/{columna_entidad}/{dias}/data.csv"

        if not os.path.exists(data_csv_path):
            print(f"Error: el archivo de datos '{data_csv_path}' no existe.")
            status_queue.put(
                manage_umbral_status(
                    request_hash=request_hash,
                    fecha=fecha,
                    dias=dias,
                    entidad=columna_entidad,
                    status="no data"
                )
            )
            return 
        
        save_to_csv(data_df, data_csv_path)
        status_queue.put(
            manage_umbral_status(
                request_hash=request_hash,
                fecha=fecha,
                dias=dias,
                entidad=columna_entidad,
                status="execute_data"
            )
        )
        result_csv_path = f"./umbrales_csv/{fecha}/{columna_entidad}/{dias}/results.csv"
        csv_to_results_umbrales(data_df, result_csv_path,dias,columna_entidad)        

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
                status="error",
                message=str(e)
            )
        )
        