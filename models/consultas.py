from pydantic import BaseModel
from typing import List, Optional
from datetime import date



class Consulta1Response(BaseModel):
    fecha_inicio: Optional[str]
    fecha_fin: Optional[str]
    folios_encontrados: Optional[List[str]] 
