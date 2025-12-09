from threading import Lock
import calendar
from datetime import date, datetime
from fastapi import BackgroundTasks
from fastapi.encoders import jsonable_encoder
from core.anomalias import calcular_anomalias
from core.manager_score import ManagerPickle
from core.manager_umbral import process_umbral_data
from core.repo_umbrales.execute_umbrales import process_umbral_and_save_db
from core.semaforo import procesar_semaforo
from core.services import consulta_licencia, consulta_semaforo, manage_umbral_status, query_masivo,query_score_licencia,query_data_umbral
import logging
import os
from multiprocessing import  Queue
import pandas as pd
from core.utils.logging_config import setup_loggers
from models.consultas import ConsultaLicenciaRequest, SemaforoRequest

from fastapi.responses import JSONResponse, StreamingResponse
import io
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)





def to_json(df: pd.DataFrame):
    data = df.fillna("").to_dict(orient="records")
    return JSONResponse(content=jsonable_encoder(data))

FORMAT_DISPATCHER = {
    "json": to_json
}

execute_scores_map = {}
request_to_task_map = {}
task_status_map = {}
managerPickle = ManagerPickle()

def get_task_status(task_id: str):
    return task_status_map.get(task_id, {"status": "not_found"})

def propensy_score(fecha_inicio: str, fecha_fin: str, background_tasks: "BackgroundTasks"):
    logger.info(f"Petición recibida para propensy_score para fechas {fecha_inicio} a {fecha_fin}.")
    request_key = makeKeyFromFechas(fecha_inicio, fecha_fin)
    
    # Si ya existe una tarea para este request, devolver el task_id existente.
    if request_key in request_to_task_map:
        existing_task_id = request_to_task_map[request_key]
        logger.info(f"Tarea existente encontrada para {request_key}: {existing_task_id}. Devolviendo estado actual.")
        return get_task_status(existing_task_id)

    # Si no existe, crear una nueva tarea.
    task_id = str(uuid.uuid4())
    request_to_task_map[request_key] = task_id
    task_status_map[task_id] = {"status": "starting", "details": "Iniciando cálculo de propensity score."}
    
    logger.info(f"Iniciando nueva tarea en segundo plano para propensy_score. Task ID: {task_id}.")
    background_tasks.add_task(propensy_score_background, fecha_inicio, fecha_fin, task_id)
    
    return {"task_id": task_id, "status": "accepted"}

def propensy_score_background(fecha_inicio: str, fecha_fin: str, task_id: str):
    logger.info(f"Tarea {task_id}: Iniciando ejecución en segundo plano de propensy_score para fechas {fecha_inicio} a {fecha_fin}.")
    try:
        key = makeKeyFromFechas(fecha_inicio, fecha_fin)
        
        task_status_map[task_id] = {"status": "processing", "details": "Ejecutando cálculo masivo de score."}
        
        if len(execute_scores_map) == 0 or execute_scores_map.get(key) is None:
            execute_scores_map[key] = "run"
            logger.info(f"Tarea {task_id}: Ejecutando managerPickle.ejecuta_masivo por primera vez para {key}.")
            managerPickle.ejecuta_masivo(fecha_inicio, fecha_fin)
        else:
            logger.info(f"Tarea {task_id}: Consultando y ejecutando managerPickle.consulta_ejecuta_masivo para {key}.")
            managerPickle.consulta_ejecuta_masivo(fecha_inicio, fecha_fin)

        task_status_map[task_id] = {"status": "processing", "details": "Ejecutando procesos adicionales."}
        logger.info(f"Tarea {task_id}: Llamando a orquestar_calculos_adicionales.")
        orquestar_calculos_adicionales(fecha_inicio, fecha_fin, task_id)

        task_status_map[task_id] = {"status": "completed", "details": "Todos los procesos finalizaron correctamente."}
        logger.info(f"Tarea {task_id}: Ejecución en segundo plano de propensy_score finalizada correctamente.")

    except Exception as e:
        logger.error(f"Tarea {task_id}: Error durante el cálculo de score en segundo plano para la tarea {task_id}: {e}", exc_info=True)
        task_status_map[task_id] = {"status": "error", "details": str(e)}

def orquestar_calculos_adicionales(fecha_inicio, fecha_fin: str, task_id: str):
    """
    Ejecuta la secuencia de cálculos post-score: Umbrales, Anomalías y Semáforo, actualizando el estado de la tarea.
    """
    umbrales_logger = logging.getLogger('umbrales_logger') 
    logger.info(f"Tarea {task_id}: Inicia la orquestación de cálculos adicionales.")
    try:
        task_status_map[task_id] = {"status": "processing", "details": "Paso 1: Generando datos de umbrales..."}
        dias_umbral = 60
        entidad_umbral = "rut_medico"
        df_umbrales = generate_data_umbral(fecha_inicio, fecha_fin, dias_umbral, entidad_umbral)
        umbrales_logger.info(f"{task_id} : Procesando umbral {fecha_inicio}-{fecha_fin} - -> {task_id} ")
        if not df_umbrales.empty:
            umbrales_logger.info(f"Tarea {task_id}: Se generaron datos de umbrales. Se procede con el cálculo de Umbrales y Anomalías.")
            
            task_status_map[task_id] = {"status": "processing", "details": "Paso 2: Guardando resultados de umbrales en la base de datos..."}
            process_umbral_and_save_db(df_umbrales, dias_umbral, entidad_umbral)

            task_status_map[task_id] = {"status": "processing", "details": "Paso 3: Calculando anomalías..."}
            calcular_anomalias(df_umbrales)
        else:
            umbrales_logger.warning(f"Tarea {task_id}: No se generaron datos de umbrales. Se omiten los pasos de guardado de Umbrales y cálculo de Anomalías.")
            # Actualizamos el estado para que el usuario sepa que se omitieron pasos
            task_status_map[task_id] = {"status": "processing", "details": "Paso 3: Omitiendo Umbrales y Anomalías por falta de datos."}


        task_status_map[task_id] = {"status": "processing", "details": "Paso 4: Procesando el semáforo..."}
        fecha_dt = datetime.strptime(fecha_fin, "%Y-%m-%d")
        procesar_semaforo(anio=fecha_dt.year, mes=fecha_dt.month)
        
        logger.info(f"Tarea {task_id}: Procesos adicionales finalizados correctamente.")

    except Exception as e:
        umbrales_logger.error(f"Error durante los procesos adicionales para la tarea {task_id}: {e}", exc_info=True)
        raise e # Relanzamos la excepción para que sea capturada en el nivel superior.

def masivo(fecha_inicio: str, fecha_fin: str):
    from_db = query_masivo(fecha_inicio, fecha_fin)
    if from_db.empty:
        return []
    result = managerPickle.ejecuta_masivo(from_db, fecha_inicio, fecha_fin)
    return result

def propensy_score_licencia(fecha_inicio: str, fecha_fin: str):
    from_db = query_score_licencia(fecha_inicio, fecha_fin)
    return from_db

def generate_data_umbral(fecha_inicio: str, fecha_fin: str, dias: int = 60, columna_entidad: str = "rut_medico"):
    data = query_data_umbral(fecha_inicio, fecha_fin, dias, columna_entidad)
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

def consulta_licencia_from_rest(where_query: ConsultaLicenciaRequest):
    df = consulta_licencia(where_query)  
    content_type = getattr(where_query, "content_type", "json").lower()
    converter = FORMAT_DISPATCHER.get(content_type, to_json)

    return converter(df)

def process_umbral_task(fecha_inicio , fecha_fin: str, dias: int, columna_entidad: str, request_hash: str, status_queue: Queue) -> None:

    print(f"DEBUG: Entrando a process_umbral_task (PID: {os.getpid()}).")
    setup_loggers()
    print(f"DEBUG: setup_loggers() llamado en process_umbral_task (PID: {os.getpid()}).")

    # Obtener los loggers localmente después de que setup_loggers() los haya configurado
    umbrales_logger = logging.getLogger('umbrales_logger')
    anomalias_logger = logging.getLogger('anomalias_logger')
    # reclamos_logger = logging.getLogger('reclamos_logger') # No se usa directamente aquí

    try:
        umbrales_logger.info(f"hash {request_hash}: Extrayendo data.")
        status_queue.put(
            manage_umbral_status(
                request_hash=request_hash,
                fecha=fecha_inicio,
                dias=dias,
                entidad=columna_entidad,
                status="extract_data"
            )
        )
        # Ejecutar consulta y procesar datos
        data_df = generate_data_umbral(fecha_inicio,fecha_fin, dias, columna_entidad)
        umbrales_logger.info(f"hash {request_hash}: procesando data.")

        # Ojo aca la data en fecha es solo referencia para almacenar estados de ejecucion de umbrales y resultados de data
        status_queue.put(
            manage_umbral_status(
                request_hash=request_hash,
                fecha=fecha_inicio,
                dias=dias,
                entidad=columna_entidad,
                status="process_data"
            )
        )
        umbrales_logger.info(f"hash {request_hash}: guardando data.")
        process_umbral_and_save_db(data_df,dias,columna_entidad)  

        anomalias_logger.info(f"hash {request_hash}: calculando anomalias.")
        status_queue.put(
            manage_umbral_status(
                request_hash=request_hash,
                fecha=fecha_inicio,
                dias=dias,
                entidad=columna_entidad,
                status="calc_data_anomaly"
            )
        )
        calcular_anomalias(data_df)
        anomalias_logger.info(f"hash {request_hash}: guardando anomalias.")
        # Registrar estado final
        status_queue.put(
            manage_umbral_status(
                request_hash=request_hash,
                fecha=fecha_inicio,
                dias=dias,
                entidad=columna_entidad,
                status="finish"
            )
        )
    except Exception as e:
        # Es importante que el logger también esté disponible en caso de error.
        # Se obtienen localmente para asegurar que estén configurados para este proceso.
        logger = logging.getLogger(__name__) # Logger general
        umbrales_logger = logging.getLogger('umbrales_logger') # Logger específico
        
        logger.error(f"Error en el proceso de umbral (hash: {request_hash}): {e}", exc_info=True)
        umbrales_logger.error(f"Error en el proceso de umbral (hash: {request_hash}): {e}", exc_info=True)

        status_queue.put(
            manage_umbral_status(
                request_hash=request_hash,
                fecha=fecha_inicio,
                dias=dias,
                entidad=columna_entidad,
                status="error"
            )
        )

def consulta_licencias_para_semaforo_from_rest(request: SemaforoRequest):
    semaforo_logger = logging.getLogger('semaforo_logger')    
    fecha_inicio, fecha_fin = None, None
    semaforo_logger.info(f"rango {request.anio}/{request.mes}: consulta licencias para semaforos data.")
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
    semaforo_logger = logging.getLogger('semaforo_logger')    
    semaforo_logger.info(f"Consulta semaforo rango[{rango}] - rut_medicio[{rut_medico}]")
    from_db =consulta_semaforo(rango, rut_medico)
    return from_db

def run_umbral_process(fecha_inicio: str, fecha_fin: str, background_tasks: "BackgroundTasks"):
    """
    Inicia un proceso de cálculo de umbrales en segundo plano.
    """
    umbrales_logger = logging.getLogger('umbrales_logger') # Logger específico
    umbrales_logger.info(f"Petición recibida para run_umbral_process para fechas {fecha_inicio} a {fecha_fin}.")
    request_key = makeKeyFromFechas(fecha_inicio, fecha_fin)
    
    if request_key in request_to_task_map:
        existing_task_id = request_to_task_map[request_key]
        umbrales_logger.info(f"Tarea existente encontrada para {request_key}: {existing_task_id}. Devolviendo estado actual.")
        return get_task_status(existing_task_id)

    task_id = str(uuid.uuid4())
    request_to_task_map[request_key] = task_id
    task_status_map[task_id] = {"status": "starting", "details": "Iniciando cálculo de umbrales."}
    
    umbrales_logger.info(f"Iniciando nueva tarea en segundo plano para run_umbral_process. Task ID: {task_id}.")
    background_tasks.add_task(run_umbral_background, fecha_inicio, fecha_fin, task_id)
    
    return {"task_id": task_id, "status": "accepted"}

def run_umbral_background(fecha_inicio: str, fecha_fin: str, task_id: str):
    umbrales_logger = logging.getLogger('umbrales_logger') # Logger específico
    umbrales_logger.info(f"Tarea {task_id}: Iniciando ejecución en segundo plano de run_umbral_process.")
    try:
        task_status_map[task_id] = {"status": "processing", "details": "Generando datos de umbrales."}
        dias_umbral = 60
        entidad_umbral = "rut_medico"
        df_umbrales = generate_data_umbral(fecha_inicio, fecha_fin, dias_umbral, entidad_umbral)

        if not df_umbrales.empty:
            task_status_map[task_id] = {"status": "processing", "details": "Guardando resultados de umbrales en la base de datos."}
            process_umbral_and_save_db(df_umbrales, dias_umbral, entidad_umbral)
            task_status_map[task_id] = {"status": "completed", "details": "Proceso de umbrales finalizado correctamente."}
        else:
            task_status_map[task_id] = {"status": "completed", "details": "No se generaron datos de umbrales."}
        
        umbrales_logger.info(f"Tarea {task_id}: Ejecución en segundo plano de run_umbral_process finalizada.")

    except Exception as e:
        umbrales_logger.error(f"Tarea {task_id}: Error durante el cálculo de umbrales: {e}", exc_info=True)
        task_status_map[task_id] = {"status": "error", "details": str(e)}

def run_anomalias_process(fecha_inicio: str, fecha_fin: str, background_tasks: "BackgroundTasks"):
    """
    Inicia un proceso de cálculo de anomalías en segundo plano.
    """
    anomalias_logger = logging.getLogger('anomalias_logger')
    anomalias_logger.info(f"Petición recibida para run_anomalias_process para fechas {fecha_inicio} a {fecha_fin}.")
    request_key = makeKeyFromFechas(fecha_inicio, fecha_fin)
    
    if request_key in request_to_task_map:
        existing_task_id = request_to_task_map[request_key]
        anomalias_logger.info(f"Tarea existente encontrada para {request_key}: {existing_task_id}. Devolviendo estado actual.")
        return get_task_status(existing_task_id)

    task_id = str(uuid.uuid4())
    request_to_task_map[request_key] = task_id
    task_status_map[task_id] = {"status": "starting", "details": "Iniciando cálculo de anomalías."}
    
    anomalias_logger.info(f"Iniciando nueva tarea en segundo plano para run_anomalias_process. Task ID: {task_id}.")
    background_tasks.add_task(run_anomalias_background, fecha_inicio, fecha_fin, task_id)
    
    return {"task_id": task_id, "status": "accepted"}

def run_anomalias_background(fecha_inicio: str, fecha_fin: str, task_id: str):
    anomalias_logger = logging.getLogger('anomalias_logger')
    anomalias_logger.info(f"Tarea {task_id}: Iniciando ejecución en segundo plano de run_anomalias_process.")
    try:
        task_status_map[task_id] = {"status": "processing", "details": "Generando datos para el cálculo de anomalías."}
        dias_umbral = 60 # Por mientras
        entidad_umbral = "rut_medico" # por mientras.. agragar despues a un request para ano.
        df_data = generate_data_umbral(fecha_inicio,fecha_fin, dias_umbral, entidad_umbral)

        if not df_data.empty:
            task_status_map[task_id] = {"status": "processing", "details": "Calculando anomalías."}
            calcular_anomalias(df_data)
            task_status_map[task_id] = {"status": "completed", "details": "Proceso de anomalías finalizado correctamente."}
        else:
            task_status_map[task_id] = {"status": "completed", "details": "No se generaron datos para el cálculo de anomalías."}

        anomalias_logger.info(f"Tarea {task_id}: Ejecución en segundo plano de run_anomalias_process finalizada.")

    except Exception as e:
        anomalias_logger.error(f"Tarea {task_id}: Error durante el cálculo de anomalías: {e}", exc_info=True)
        task_status_map[task_id] = {"status": "error", "details": str(e)}
