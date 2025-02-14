from typing import List
from core.manager_pickle import ManagerPickle
from core.services import busca_datos_consulta1


def consulta1(folios: List[str], fecha_inicio: str, fecha_fin: str):
    from_db = busca_datos_consulta1(folios, fecha_inicio, fecha_fin)  
    result = ManagerPickle().execute(
        "businessModel", "consulta", from_db.folios_encontrados, from_db.fecha_inicio, from_db.fecha_fin
    )
    return {"status": "success", "data": result}
