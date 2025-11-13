import json
import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from cron_priorizacion import run_cron_priorizacion
import os
# Usamos el logger estándar aquí, ya que este módulo es de configuración
logger = logging.getLogger(__name__)

def start_scheduler():
    """
    Inicia el planificador de tareas en segundo plano para ejecutar el cron de priorización.
    """

    try:
        scheduler = BackgroundScheduler(timezone="UTC")
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cron_config_path = os.path.join(base_dir, 'cron_priorizacion.json')

        with open(cron_config_path, 'r') as f:
            cron_config = json.load(f)
        
        cron_expression = cron_config['times']['cron']
        
        scheduler.add_job(
            run_cron_priorizacion,
            trigger=CronTrigger.from_crontab(cron_expression),
            id="cron_priorizacion_job",
            name="Ejecuta el proceso de priorización de reclamos",
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("Planificador de tareas iniciado correctamente.")
        logger.info(f"[PID: {os.getpid()}] >Trabajo 'cron_priorizacion_job' programado con la expresión: '{cron_expression}'")

    except FileNotFoundError:
        logger.error(f"[PID: {os.getpid()}] >No se encuentra el archivo de configuración del cron en: {cron_config_path}")
    except Exception as e:
        logger.error(f"[PID: {os.getpid()}] >Error al iniciar el planificador de tareas: {e}", exc_info=True)
