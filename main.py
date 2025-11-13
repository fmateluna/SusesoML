from fastapi import FastAPI
from api.endpoints import router as api_router
from core.scheduler import start_scheduler
import threading
from cron_priorizacion import run_cron_priorizacion
import logging
from core.utils.logging_config import setup_loggers

app = FastAPI(title="Manager Pickle Server")

@app.on_event("startup")
def startup_event():
    """
    Al iniciar la aplicación:
    1. Configura todos los loggers personalizados.
    2. Inicia el planificador de tareas para las ejecuciones programadas.
    3. Ejecuta la priorización de reclamos una vez en un hilo separado.
    """
    # 1. Configura los loggers para toda la aplicación
    setup_loggers()
    
    # 2. Inicia el planificador para las ejecuciones futuras (semanales)
    logging.info("Iniciando el planificador de tareas programadas.")
    start_scheduler()

    # 3. Ejecuta la tarea de priorización una vez, en un hilo no bloqueante
    logging.info("Iniciando la ejecución única de priorización de reclamos al arranque.")
    thread = threading.Thread(target=run_cron_priorizacion)
    thread.start()

# Registrar el router con el prefijo '/lm/ml'
app.include_router(api_router, prefix="/lm/ml")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)