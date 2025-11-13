import logging
import os

def setup_loggers():
    """
    Configura y registra todos los loggers personalizados de la aplicación.
    Esta función debe ser llamada una sola vez al inicio de la aplicación.
    """
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    loggers_config = {
        'priorizacron_logger': 'priorizacron.log',
        'reclamos_logger': 'reclamos.log',
        'umbrales_logger': 'umbrales.log',
        'anomalias_logger': 'anomalias.log',
        'semaforo_logger': 'semaforo.log'
    }

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    for logger_name, log_file in loggers_config.items():
        logger = logging.getLogger(logger_name)
        
        # --- MODIFICACIÓN CRÍTICA PARA MULTIPROCESSING ---
        # Limpiar todos los manejadores existentes para asegurar un estado limpio.
        # Esto es vital en procesos hijos que pueden heredar manejadores no funcionales.
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close() # Cerrar el manejador para liberar recursos del archivo
        # --- FIN MODIFICACIÓN CRÍTICA ---

        logger.setLevel(logging.INFO)
        
        # Crear el manejador de archivo
        file_handler = logging.FileHandler(os.path.join(log_dir, log_file), encoding='utf-8')
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        
        # Evitar que los logs se propaguen al logger raíz (consola)
        logger.propagate = False

    print(f"[PID: {os.getpid()}] >Loggers configurados correctamente en el proceso {os.getpid()}.")

