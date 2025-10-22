from functools import wraps
from sqlalchemy.exc import SQLAlchemyError
from core.database import SessionLocal
import logging

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
            logger.error(f"Error de base de datos en {func.__name__}: {str(e)}")
            raise ValueError(f"Error de base de datos: {str(e)}") from e
        except Exception as e:
            session.rollback()
            logger.error(f"Error inesperado en {func.__name__}: {str(e)}")
            raise ValueError(f"Error inesperado: {str(e)}") from e
        finally:
            session.close()
    return wrapper
