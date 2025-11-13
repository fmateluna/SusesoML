import datetime
import json
import os
import logging
import hashlib # Import hashlib
from core.repo_reclamos.reclamos import procesa_reclamos
from models.consultas import ReclamosRequest
from core.services import save_reclamos_data_summary # Import the new function

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

        # Generar un hash para la solicitud
        # Incluimos rut_medico en el hash, aunque sea None por defecto
        request_params_str = f"{current_anio}-{current_mes}-{request.rut_medico}"
        request_hash = hashlib.md5(request_params_str.encode('utf-8')).hexdigest()

        # Registrar el inicio del procesamiento en la base de datos
        save_reclamos_data_summary(
            request_hash=request_hash,
            anio=current_anio,
            mes=current_mes,
            rut_medico=request.rut_medico,
            status="processing"
        )

        # Ejecutar el proceso de reclamos
        procesa_reclamos(request)
        
        priorizacron_logger.info(f"[PID: {os.getpid()}] >Finaliza la ejecución del cron de priorización para el período: {current_anio}-{current_mes:02d}.")

        # Registrar el éxito del procesamiento en la base de datos
        save_reclamos_data_summary(
            request_hash=request_hash,
            anio=current_anio,
            mes=current_mes,
            rut_medico=request.rut_medico,
            status="completed"
        )

    except Exception as e:
        priorizacron_logger.error(f"[PID: {os.getpid()}] >Error durante la ejecución del cron de priorización de reclamos: {e}", exc_info=True)
        # Registrar el error en la base de datos
        # Asegurarse de que request_hash esté definido incluso si el error ocurre antes de su generación
        if 'request_hash' in locals():
            save_reclamos_data_summary(
                request_hash=request_hash,
                anio=current_anio,
                mes=current_mes,
                rut_medico=request.rut_medico,
                status="error"
            )
        else:
            # Si el error ocurre antes de generar el hash, loguear sin hash específico
            priorizacron_logger.error(f"[PID: {os.getpid()}] >Error crítico antes de generar request_hash: {e}", exc_info=True)


if __name__ == "__main__":
    from core.utils.logging_config import setup_loggers
    setup_loggers()
    run_cron_priorizacion()
