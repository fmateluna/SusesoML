from dataclasses import dataclass
from datetime import date, datetime
from multiprocessing import Process, Queue
import asyncio
import multiprocessing
import time
import os
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from core.manager import (
    FORMAT_DISPATCHER, 
    consulta_licencia_from_rest, 
    consulta_licencias_para_semaforo_from_rest,
    consulta_rest_semaforo,  
    process_umbral_task, 
    propensy_score,
    propensy_score_licencia,
    get_task_status,
    run_umbral_process,
    run_anomalias_process
)
from typing import Optional
import hashlib
import logging
from threading import Thread
from core.repo_reclamos.reclamos import procesa_reclamos
from core.semaforo import procesar_semaforo
from core.services import  consulta_semaforo, get_umbral_status, manage_umbral_status
from models.consultas import ConsultaLicenciaRequest, MasivoRequest, ReclamosRequest, SemaforoRequest, UmbralRequest
from core.utils.task_manager import task_manager
from threading import Thread, Lock
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

cache_lock = Lock()
long_query_cache = {}


def generate_request_hash(request_model) -> str:
    # Convierte el Pydantic model a dict y luego genera hash
    return hashlib.md5(str(request_model.dict()).encode()).hexdigest()


def async_query_task(request_hash: str, request_model, func):
    try:
        with cache_lock:
            long_query_cache[request_hash] = {"status": "processing", "updated_at": datetime.now()}
        result = func(request_model)
        with cache_lock:
            result_json = result.to_dict(orient="records")
            long_query_cache[request_hash] = {"status": "finishi", "updated_at": datetime.now(), "data":result_json}

    except Exception as e:
        with cache_lock:
            long_query_cache[request_hash] = {"status": "error", "message": str(e), "updated_at": datetime.now()}


def check_or_start_task(request_model, func):
    request_hash = generate_request_hash(request_model)
    with cache_lock:
        if request_hash in long_query_cache:
            return long_query_cache[request_hash]
    Thread(target=async_query_task, args=(request_hash, request_model, func)).start()
    return {"status": "processing", "message": "working."}

@router.post("/score")
def execute_score(request: MasivoRequest, background_tasks: BackgroundTasks):
    """
    Inicia un proceso de cálculo de propensity score en segundo plano 
    y devuelve un ID de tarea para seguimiento.
    """
    try:
        response = propensy_score(request.fecha_inicio, request.fecha_fin, background_tasks)
        return response
    except Exception as e:
        logger.error(f"Error initiating score calculation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")

@router.get("/score/status/{task_id}")
def get_score_status(task_id: str):
    """Consulta el estado de una tarea de cálculo de score."""
    return get_task_status(task_id)

@router.post("/umbrales")
def execute_umbrales(request: MasivoRequest, background_tasks: BackgroundTasks):
    """
    Inicia un proceso de cálculo de umbrales en segundo plano.
    """
    try:
        response = run_umbral_process(request.fecha_inicio, request.fecha_fin, background_tasks)
        return response
    except Exception as e:
        logger.error(f"Error initiating umbral calculation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")

@router.get("/umbrales/status/{task_id}")
def get_umbrales_status(task_id: str):
    """Consulta el estado de una tarea de cálculo de umbrales."""
    return get_task_status(task_id)

@router.post("/anomalias")
def execute_anomalias(request: MasivoRequest, background_tasks: BackgroundTasks):
    """
    Inicia un proceso de cálculo de anomalías en segundo plano.
    """
    try:
        response = run_anomalias_process(request.fecha_inicio, request.fecha_fin, background_tasks)
        return response
    except Exception as e:
        logger.error(f"Error initiating anomalias calculation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")

@router.get("/anomalias/status/{task_id}")
def get_anomalias_status(task_id: str):
    """Consulta el estado de una tarea de cálculo de anomalías."""
    return get_task_status(task_id)
    
@router.post("/score/details")
def query_score_details(request: MasivoRequest):
    """Consulta de propensity score y devuelve los resultados."""
    try:
        data = propensy_score_licencia(request.fecha_inicio,request.fecha_fin)
        return data
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": f"Error inesperado: {str(e)}"}
    
@router.post("/umbral/create")
async def create_umbral(request: UmbralRequest):
    """Inicia una consulta de umbral y registra su estado en ml.umbral_data."""
    # Configurar el logging de multiprocessing para que los errores del proceso hijo se dirijan a stderr
    multiprocessing.log_to_stderr(logging.INFO)
    try:
        request_hash = task_manager.generate_request_hash(request)

        status = get_umbral_status(request_hash)
        if status is not None:
            if status["status"] != "not_found" and status["status"] != "error" :
                return status

        manage_umbral_status(
            request_hash=request_hash,
            fecha=request.fecha,
            dias=request.dias,
            entidad=request.columna_entidad,
            status="init"
        )

        status_queue = Queue()

        process = Process(
            target=process_umbral_task,
            args=(request.fecha, request.dias, request.columna_entidad, request_hash, status_queue)
        )
        process.start()

        return get_umbral_status(request_hash)

    except Exception as e:
        logger.error(f"Error initiating request: {str(e)}")
        return {"status": "error", "message": f"Error inesperado: {str(e)}"}


@router.get("/umbral/status/{request_hash}")
async def get_umbral_status_endpoint(request_hash: str):
    """Check the status of a query by its request hash."""
    return get_umbral_status(request_hash)

@router.post("/licencias/query")
def query_licencias(request: ConsultaLicenciaRequest):
    return task_manager.check_or_start_task(request, consulta_licencia_from_rest)


from fastapi import BackgroundTasks

@router.post("/semaforo")
async def procesar_semaforo_endpoint(
    request: SemaforoRequest,
    background_tasks: BackgroundTasks
):
    rango = f"{request.anio}-{request.mes:02d}"
    resultado_cacheado = consulta_semaforo(rango, request.rut_medico)

    if len(resultado_cacheado) > 0:
        respuesta = resultado_cacheado
    else:
        respuesta = []  

    def tarea_recalculo(req_model: SemaforoRequest):
        df_calculos = consulta_licencias_para_semaforo_from_rest(req_model)
        procesar_semaforo(
            df_calculos=df_calculos,
            mes=req_model.mes,
            anio=req_model.anio,
            sort_values_by=req_model.sort_values_by,
            umbral_decorte=req_model.umbral_decorte,
            rn_ln_mes=req_model.rn_ln_mes,
            umbral_deanomalias=req_model.umbral_deanomalias
        )

    background_tasks.add_task(tarea_recalculo, request)
    return respuesta
     
@router.post("/licencias/reclamos")
def query_reclamos(request: ReclamosRequest):
    return procesa_reclamos(request)

@router.get("/semaforo/{rango_path}")
def query_semaforo(rango_path : str):
    semaforo_logger = logging.getLogger('semaforo_logger')   
    semaforo_logger.info(f"Consulta semaforo en rest get rango[{rango_path}]")
    return consulta_rest_semaforo(rango=rango_path,rut_medico=None)