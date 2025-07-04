from core.manager_pickle import ManagerPickle
from core.services import query_regla_negocio1,query_masivo


def consulta1(
    fecha_inicio: str,
    fecha_fin: str,
    especialidad_profesional: str,
    cod_diagnostico_principal: str,
    nombre_columna: str,
):
    from_db = query_regla_negocio1(
        cod_diagnostico_principal, especialidad_profesional, fecha_inicio, fecha_fin
    )
    #Ojo procesar y luego listar scored
    if from_db.empty:
        return []
    result = ManagerPickle().ejecuta_regla_negocio1(
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