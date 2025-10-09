from dataclasses import dataclass
from datetime import date
from multiprocessing import Process, Queue
import asyncio
import time
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from core.manager import FORMAT_DISPATCHER, consulta_licencia_from_rest, consulta_semaforo_from_rest,  process_umbral_task, propensy_score,propensy_score_licencia
from typing import Optional
import hashlib
import logging
from fastapi import APIRouter
from threading import Thread, Lock
from datetime import datetime
import hashlib
from core.semaforo import procesar_semaforo
from core.services import  consulta_semaforo, get_umbral_status, manage_umbral_status
from models.consultas import ConsultaLicenciaRequest, MasivoRequest, SemaforoRequest, UmbralRequest
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
status_store = {}

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
def execute_score(request: MasivoRequest):
    """Ejecuta la consulta de resumen de propensity score y devuelve los resultados."""
    try:
        response = propensy_score(request.fecha_inicio,request.fecha_fin)
        return {"status": "working", "data": response}
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": f"Error inesperado: {str(e)}"}
    
@router.post("/score/details")
def query_score(request: MasivoRequest):
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
        request_hash = generate_request_hash(request)

        # Consultar si el estado ya existe
        status = get_umbral_status(request_hash)
        if status is not None:
            if status["status"] != "not_found" and status["status"] != "error" :
                return status

        # Registrar estado inicial
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
def query_score(request: ConsultaLicenciaRequest):
    return check_or_start_task(request, consulta_licencia_from_rest)


@router.post("/semaforo")
def procesar_semaforo_endpoint(request: SemaforoRequest):
    rango = f"{request.anio}-{request.mes:02d}"
    resultado = consulta_semaforo(rango, request.rut_medico)
    if len(resultado)>0:
        return resultado

    def semaforo_func(req_model):
        df_calculos = consulta_semaforo_from_rest(req_model)
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
    
    resultado = check_or_start_task(request, semaforo_func)
    return resultado
     