from functools import wraps
from sqlalchemy.exc import SQLAlchemyError
from core.database import SessionLocal
import logging
import os

from core.pae_database import PaeSessionLocal # Import new session

logger = logging.getLogger(__name__)

def db_session(func):
    """
    Decorador para gestionar la sesión de SQLAlchemy.
    Abre una sesión, ejecuta la función, hace commit si no hay errores,
    hace rollback si hay errores y cierra la sesión.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        session = SessionLocal()
        try:
            result = func(session, *args, **kwargs)
            session.commit()
            return result
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"[PID: {os.getpid()}] >Error de base de datos en {func.__name__}: {str(e)}")
            raise ValueError(f"[PID: {os.getpid()}] >Error de base de datos: {str(e)}") from e
        except Exception as e:
            session.rollback()
            logger.error(f"[PID: {os.getpid()}] >Error inesperado en {func.__name__}: {str(e)}")
            raise ValueError(f"[PID: {os.getpid()}] >Error inesperado: {str(e)}") from e
        finally:
            session.close()
    return wrapper

# fmateluna : Se agrega un decorador para la nueva base de datos pae_sabana
def pae_db_session(func):
    """
    Decorador para gestionar la sesión de SQLAlchemy para la base de datos PAE.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        session = PaeSessionLocal()
        try:
            result = func(session, *args, **kwargs)
            session.commit()
            return result
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"[PID: {os.getpid()}] >Error de base de datos PAE en {func.__name__}: {str(e)}")
            raise ValueError(f"[PID: {os.getpid()}] >Error de base de datos PAE: {str(e)}") from e
        except Exception as e:
            session.rollback()
            logger.error(f"[PID: {os.getpid()}] >Error inesperado en {func.__name__}: {str(e)}")
            raise ValueError(f"[PID: {os.getpid()}] >Error inesperado: {str(e)}") from e
        finally:
            session.close()
    return wrapper
