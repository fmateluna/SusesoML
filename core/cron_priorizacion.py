# core/cron_priorizacion.py
import sys
import os
from datetime import datetime
import logging

# Añadir el directorio raíz del proyecto al sys.path
# para asegurar que los módulos se puedan importar correctamente
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.repo_reclamos.reclamos import procesa_reclamos
from models.consultas import ReclamosRequest
from core.services import guardar_priorizacion, guardar_priorizacion_historica
from core.utils.custom_logger import get_custom_logger

# Configurar logger para este módulo
logger = get_custom_logger('cron_priorizacion', 'cron_priorizacion.log')

def ejecutar_proceso_priorizacion():
    """
    Cron de ejecucion Prioritario : Orquesta el proceso completo de priorización de denuncias.
    1. Crea una solicitud para el mes y año actual.
    2. Ejecuta el proceso de reclamos para obtener los puntajes de priorización.
    3. Transforma los resultados al formato requerido, es decir :
    priorización
    "folio_fui": 1169848, "rut_medico": "26909627-6", "fecha_ingreso": "2025-06-02T00:00:00", "sancionado": "No", "no_admisible": "sin decision", "ptje_prio": 0, "decision": "sin decision", "fecha_actualizacion": "2025-06-30T00:00:00"

    4. Guarda cada resultado en las tablas 'priorizacion' y 'priorizacion_historica'.
    """
    try:
        now = datetime.now()
        #cron: Se crea un request para el mes y año actual.
        request = ReclamosRequest(anio=now.year, mes=now.month)
        
        logger.info(f"Iniciando proceso de priorización para {now.year}-{now.month}")
        
        #cron: Se ejecuta el procesamiento de reclamos.
        resultados = procesa_reclamos(request)
        
        if not resultados:
            logger.info("No se encontraron resultados para procesar.")
            return

        logger.info(f"Se procesarán {len(resultados)} resultados.")

        for resultado in resultados:
            #cron: Se transforma el resultado al formato deseado.
            sancionado_bool = True if resultado.get("sancionado") == 'Si' else False
            no_admisible_bool = True if resultado.get("no_admisible") == 'Si' else False

            datos_para_guardar = {
                "denuncia_id": resultado.get("folio_fui"),
                "rut_medico": resultado.get("rut_medico"),
                "fecha_ingreso": resultado.get("fecha_ingreso"),
                "sancionado": sancionado_bool,
                "no_admisible": no_admisible_bool,
                "valor_priorizacion": resultado.get("ptje_prio"),
                "decision": resultado.get("decision"),
                "fecha_actualizacion": now,
                "fecha_creacion": now
            }

            #cron: Se guarda en la tabla de priorización (último valor).
            guardar_priorizacion(datos_para_guardar)
            
            #cron: Se guarda en la tabla histórica.(Existe un trigger que se encagar de dejar solo antiguedad de 7 meses)
            guardar_priorizacion_historica(datos_para_guardar)

        logger.info("Proceso de priorización finalizado exitosamente.")

    except Exception as e:
        logger.error(f"Error en el proceso de priorización: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    """
    Cron de ejecucion Prioritario : Punto de entrada para ejecución manual.
    Permite probar el proceso de priorización directamente desde la línea de comandos.
    """
    logger.info("Ejecución manual del proceso de priorización iniciada.")
    ejecutar_proceso_priorizacion()
    logger.info("Ejecución manual del proceso de priorización finalizada.")
