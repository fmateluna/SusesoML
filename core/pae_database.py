# fmateluna : Se crea este archivo para manejar la nueva conexion a la base de datos pae_sabana
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# fmateluna : Configuracion para loggear las queries de SQLAlchemy
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

DB_SUSESO_HOST = os.getenv("DB_SUSESO_HOST")
DB_SUSESO_PORT = os.getenv("DB_SUSESO_PORT")
DB_SUSESO_NAME = os.getenv("DB_SUSESO_NAME")
DB_SUSESO_USER = os.getenv("DB_SUSESO_USER")
DB_SUSESO_PASS = os.getenv("DB_SUSESO_PASS")

SQLALCHEMY_PAE_DATABASE_URL = f"postgresql://{DB_SUSESO_USER}:{DB_SUSESO_PASS}@{DB_SUSESO_HOST}:{DB_SUSESO_PORT}/{DB_SUSESO_NAME}"
pae_engine = create_engine(SQLALCHEMY_PAE_DATABASE_URL, pool_size=10, max_overflow=20, pool_timeout=30)
PaeSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=pae_engine)
