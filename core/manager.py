from core.manager_pickle import ManagerPickle
from core.services import query_regla_negocio,query_masivo,query_score,query_score_licencia

execute_scores_map = {}

def consulta_unitaria(
    fecha_inicio: str,
    fecha_fin: str,
    especialidad_profesional: str,
    cod_diagnostico_principal: str,
    nombre_columna: str,
):
    from_db = query_regla_negocio(
        cod_diagnostico_principal, especialidad_profesional, fecha_inicio, fecha_fin
    )
    #Ojo procesar y luego listar scored
    if from_db.empty:
        return []
    result = ManagerPickle().ejecuta_regla_negocio(
        "business_rule_model",
        from_db,
        nombre_columna,
        cod_diagnostico_principal,
        especialidad_profesional,
    )
    return result


def masivo(fecha_inicio: str, fecha_fin: str):
    from_db = query_masivo(fecha_inicio, fecha_fin)
    if from_db.empty:
        return []
    result = ManagerPickle().ejecuta_masivo(from_db, fecha_inicio, fecha_fin)
    return result

def propensy_score(fecha_inicio: str, fecha_fin: str):
    key = makeKeyFromFechas(fecha_inicio, fecha_fin)
    
    if len(execute_scores_map) == 0 or execute_scores_map.get(key) is None:
        from_db = query_masivo(fecha_inicio, fecha_fin)
        if from_db.empty:
            return []
        ManagerPickle().ejecuta_masivo(from_db, fecha_inicio, fecha_fin)
        execute_scores_map[key] = "run"
    
    from_db = query_score(fecha_inicio, fecha_fin)
    return from_db

def propensy_score_licencia(fecha_inicio: str, fecha_fin: str):
    from_db = query_score_licencia(fecha_inicio, fecha_fin)
    return from_db

def makeKeyFromFechas(fecha_inicio: str, fecha_fin: str):
    """
    Genera una clave única basada en fecha_inicio y fecha_fin.
    """
    return f"{fecha_inicio}_{fecha_fin}"    