from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from core.manager import consulta_unitaria,masivo,propensy_score,propensy_score_licencia

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


@router.post("/negocio1/consulta")
async def consulta(request: ConsultaRequest):
    """
    Endpoint para ejecutar la función 'consulta' del archivo businessModel.pkl.
    """
    try:
        result = consulta_unitaria(
            request.fecha_inicio,
            request.fecha_fin,
            request.especialidad_profesional,
            request.cod_diagnostico_principal,
            request.nombre_columna,
        )
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error ejecutando el pickle: {str(e)}"
        )
        
@router.post("/masivo")
async def masiva(request: MasivoRequest, background_tasks: BackgroundTasks):
    """
    Endpoint para ejecutar la función 'consulta' del archivo businessModel.pkl.
    
            background_tasks.add_task(
            ManagerPickle().ejecuta_masivo(from_db, fecha_inicio, fecha_fin)
        )   
    
    """
    try:
        result = masivo(
            request.fecha_inicio,
            request.fecha_fin
        )
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error ejecutando el pickle: {str(e)}"
        )
        
@router.post("/score")
def execute_score(request: MasivoRequest):
    """Ejecuta la consulta de resumen de propensity score y devuelve los resultados."""
    try:
        data = propensy_score(request.fecha_inicio,request.fecha_fin)

        return {"status": "success", "data": data}

    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": f"Error inesperado: {str(e)}"}
    
@router.post("/score/details")
def query_score(request: MasivoRequest):
    """Ejecuta la consulta de resumen de propensity score y devuelve los resultados."""
    try:
        data = propensy_score_licencia(request.fecha_inicio,request.fecha_fin)

        return data

    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": f"Error inesperado: {str(e)}"}