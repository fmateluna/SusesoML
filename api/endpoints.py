from dataclasses import dataclass
from datetime import date
from multiprocessing import Process, Queue
import asyncio
import time
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from core.manager import consulta_lincencia_from_rest, process_umbral_task, propensy_score,propensy_score_licencia,generate_data_umbral
from typing import Optional
import hashlib
import logging

from core.services import get_umbral_status, manage_umbral_status
from models.consultas import ConsultaLicenciaRequest, MasivoRequest, UmbralRequest
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
status_store = {}


def generate_request_hash(request: UmbralRequest) -> str:
    """Generate a unique hash for the request content."""
    request_str = f"{request.fecha}:{request.dias}:{request.columna_entidad}"
    return hashlib.md5(request_str.encode()).hexdigest()
     
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
async def create_umbral(request: UmbralRequest, background_tasks: BackgroundTasks):
    """Inicia una consulta de umbral y registra su estado en ml.umbral_data."""
    try:
        request_hash = generate_request_hash(request)

        # Consultar si el estado ya existe
        status = get_umbral_status(request_hash)
        if status["status"] != "not_found":
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

        background_tasks.add_task(monitor_status, request_hash, status_queue)

        return {
            "status": "init",
            "request_hash": request_hash
        }

    except Exception as e:
        logger.error(f"Error initiating request: {str(e)}")
        return {"status": "error", "message": f"Error inesperado: {str(e)}"}

async def monitor_status(request_hash: str, status_queue: Queue):
    """Monitor the status of the background task."""
    while True:
        if not status_queue.empty():
            status_update = status_queue.get()
            manage_umbral_status(
                request_hash=status_update["request_hash"],
                fecha=status_update.get("fecha"),
                dias=status_update.get("dias"),
                entidad=status_update.get("entidad"),
                status=status_update["status"],
                execution_time=status_update.get("execution_time"),
                message=status_update.get("message")
            )
            if status_update["status"] in ["finish", "error"]:
                break
        await asyncio.sleep(0.1)

@router.get("/umbral/status/{request_hash}")
async def get_umbral_status_endpoint(request_hash: str):
    """Check the status of a query by its request hash."""
    return get_umbral_status(request_hash)

@router.post("/licencias/query")
def query_score(request: ConsultaLicenciaRequest):
    """Consulta todos los datos de licencias."""
    try:
        data = consulta_lincencia_from_rest(request)
        return data

    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": f"Error inesperado: {str(e)}"}