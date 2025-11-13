import logging
import os

def get_custom_logger(log_name: str, log_file: str):
    """
    Configura y devuelve un logger personalizado que escribe en un archivo de log específico.
    Evita la duplicación de manejadores si el logger ya ha sido configurado previamente.

    Args:
        log_name (str): El nombre único para el logger.
        log_file (str): El nombre del archivo donde se registrarán los eventos (ej. 'umbrales.log').

    Returns:
        logging.Logger: La instancia del logger configurado.
    """
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger(log_name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler(os.path.join(log_dir, log_file))
        formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%d-%m-%Y %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False

    return logger
