from core.manager_pickle import ManagerPickle
from core.services import query_masivo,query_score_licencia

execute_scores_map = {}
managerPickle =  ManagerPickle()

def masivo(fecha_inicio: str, fecha_fin: str):
    from_db = query_masivo(fecha_inicio, fecha_fin)
    if from_db.empty:
        return []
    result = managerPickle.ejecuta_masivo(from_db, fecha_inicio, fecha_fin)
    return result

def propensy_score(fecha_inicio: str, fecha_fin: str):
    key = makeKeyFromFechas(fecha_inicio, fecha_fin)

    # Consulta si l ejecucion masiva ya se realizo por los parametros de fechas del request
    if len(execute_scores_map) == 0 or execute_scores_map.get(key) is None:        
        execute_scores_map[key] = "run"
        return managerPickle.ejecuta_masivo( fecha_inicio, fecha_fin)
    return managerPickle.consulta_ejecuta_masivo(fecha_inicio, fecha_fin)

def propensy_score_licencia(fecha_inicio: str, fecha_fin: str):
    from_db = query_score_licencia(fecha_inicio, fecha_fin)
    return from_db

def makeKeyFromFechas(fecha_inicio: str, fecha_fin: str):
    """
    Genera una clave única basada en fecha_inicio y fecha_fin.
    """
    return f"{fecha_inicio}_{fecha_fin}"    