import datetime
import json
import os
import logging
from core.repo_reclamos.reclamos import procesa_reclamos
from models.consultas import ReclamosRequest

# Obtiene el logger que ya fue configurado en main.py
priorizacron_logger = logging.getLogger('priorizacron_logger')

def run_cron_priorizacion():
    
    try:
        # Obtener el año y mes actual para la solicitud
        now = datetime.datetime.now()
        current_anio = now.year
        current_mes = now.month
        
        priorizacron_logger.info(f"[PID: {os.getpid()}] >Inicia la ejecución del cron de priorización de reclamos para el período: {current_anio}-{current_mes:02d}.")

        # Crear una instancia de ReclamosRequest para el mes y año actuales
        # Se asume que ReclamosRequest puede ser instanciado con anio y mes
        request = ReclamosRequest(anio=current_anio, mes=current_mes)

        # Ejecutar el proceso de reclamos
        procesa_reclamos(request)
        
        priorizacron_logger.info(f"[PID: {os.getpid()}] >Finaliza la ejecución del cron de priorización para el período: {current_anio}-{current_mes:02d}.")
    except Exception as e:
        priorizacron_logger.error(f"[PID: {os.getpid()}] >Error durante la ejecución del cron de priorización de reclamos: {e}", exc_info=True)

if __name__ == "__main__":
    from core.utils.logging_config import setup_loggers
    setup_loggers()
    run_cron_priorizacion()
