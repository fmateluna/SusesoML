from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from core.manager import propensy_score,propensy_score_licencia

router = APIRouter()


# Modelo para validar la entrada
class ConsultaRequest(BaseModel):
    especialidad_profesional: str
    cod_diagnostico_principal: str
    nombre_columna: str
    fecha_inicio: str
    fecha_fin: str
    
# Modelo para validar la entrada
class MasivoRequest(BaseModel):
    fecha_inicio: str
    fecha_fin: str    


     
@router.post("/score")
def execute_score(request: MasivoRequest):
    """Ejecuta la consulta de resumen de propensity score y devuelve los resultados."""
    try:
        response = propensy_score(request.fecha_inicio,request.fecha_fin)
        return {"status": "working", "data": response}
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": f"Error inesperado: {str(e)}"}
    
@router.post("/score/details")
def query_score(request: MasivoRequest):
    """Consulta de propensity score y devuelve los resultados."""
    try:
        data = propensy_score_licencia(request.fecha_inicio,request.fecha_fin)

        return data

    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": f"Error inesperado: {str(e)}"}