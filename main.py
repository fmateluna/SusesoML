from fastapi import FastAPI
from api.endpoints import router as api_router
from core.scheduler import start_scheduler
import threading
from core.cron_priorizacion import ejecutar_proceso_priorizacion
import logging
from core.utils.logging_config import setup_loggers
import multiprocessing # Importar multiprocessing

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
    
    # 2. Inicia el planificador para las ejecuciones futuras
    logging.info("Iniciando el planificador de tareas programadas.")
    start_scheduler()

# Registrar el router con el prefijo '/lm/ml'
app.include_router(api_router, prefix="/lm/ml")

if __name__ == "__main__":
    # Asegura que el método de inicio de multiprocessing sea 'spawn' para mayor robustez, especialmente en Windows.
    # Esto debe hacerse antes de que se creen objetos Process.
    multiprocessing.set_start_method('spawn', force=True)
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)