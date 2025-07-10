from fastapi import FastAPI
from api.endpoints import router as api_router
from models import BusinessModel

app = FastAPI(title="Manager Pickle Server")

# Registrar el router con el prefijo '/lm/ml'
app.include_router(api_router, prefix="/lm/ml")

if __name__ == "__main__":
    import uvicorn
    # Desactivar recarga automática para evitar problemas con pickles
    BusinessModel.__module__ = '__main__'
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)