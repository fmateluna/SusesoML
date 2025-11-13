from dataclasses import dataclass
from datetime import date
from multiprocessing import Process, Queue
import asyncio
import time
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from core.manager import (
    FORMAT_DISPATCHER, 
    consulta_licencia_from_rest, 
    consulta_semaforo_from_rest,  
    process_umbral_task, 
    propensy_score,
    propensy_score_licencia,
    get_task_status as get_score_task_status
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

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
    return get_score_task_status(task_id)
    
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


from core.utils.custom_logger import get_custom_logger
# ... (otras importaciones)

# Configura el logger para este módulo, si es necesario, o usa el logger raíz.
# Para el endpoint de semáforo, usaremos su logger personalizado.
semaforo_logger = get_custom_logger('semaforo_logger', 'semaforo.log')

# ... (otro código)

@router.post("/semaforo")
def procesar_semaforo_endpoint(request: SemaforoRequest):
    semaforo_logger.info(f"Recibida petición para procesar semáforo: mes={request.mes}, anio={request.anio}")
    rango = f"{request.anio}-{request.mes:02d}"
    
    # Primero, intenta obtener un resultado pre-calculado (cache).
    resultado = consulta_semaforo(rango, request.rut_medico)
    if len(resultado) > 0:
        semaforo_logger.info(f"Se encontraron resultados pre-calculados para el rango '{rango}'. Se devuelven desde la base de datos.")
        return resultado

    # Si no hay resultados, se inicia un nuevo cálculo en segundo plano.
    semaforo_logger.info(f"No se encontraron resultados pre-calculados. Se inicia una nueva tarea de cálculo para el rango '{rango}'.")
    def semaforo_func(req_model):
        df_calculos = consulta_semaforo_from_rest(req_model)
        # La función 'procesar_semaforo' ya tiene sus propios logs de inicio y fin.
        resultado = procesar_semaforo(
            df_calculos=df_calculos,
            mes=req_model.mes,
            anio=req_model.anio,
            sort_values_by=req_model.sort_values_by,
            umbral_decorte=req_model.umbral_decorte,
            rn_ln_mes=req_model.rn_ln_mes,
            umbral_deanomalias=req_model.umbral_deanomalias
        )
        return resultado
    
    resultado = task_manager.check_or_start_task(request, semaforo_func)
    return resultado
     
@router.post("/licencias/reclamos")
def query_reclamos(request: ReclamosRequest):
    return procesa_reclamos(request)