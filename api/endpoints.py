from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from core.manager import consulta1
from core.manager_pickle import ManagerPickle

router = APIRouter()

# Modelo para validar la entrada
class ConsultaRequest(BaseModel):
    especialidad_profesional: str
    cod_diagnostico_principal: str
    nombre_columna: str    

@router.post("/negocio1/consulta")
async def consulta(request: ConsultaRequest):
    """
    Endpoint para ejecutar la función 'consulta' del archivo businessModel.pkl.
    """
    try:
        result = consulta1(
            request.especialidad_profesional, 
            request.cod_diagnostico_principal, 
            request.nombre_columna
        )
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error ejecutando el pickle: {str(e)}")
