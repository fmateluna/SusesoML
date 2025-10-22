import datetime
import time
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text, exc
from core.database import SessionLocal
import pandas as pd
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
import logging
from models.consultas import ConsultaLicenciaRequest
from datetime import datetime
from core.utils.db_utils import db_session, pae_db_session # Import new decorator

# fmateluna : Se crea esta nueva funcion para la consulta de detalle uclm
@pae_db_session
def consulta_detalle_uclm(session, anio: int, mes: int) -> list[dict]:
    """
    Consulta la tabla pae_sabana.uclmdetalle por mes y año.
    """
    query = read_sql_file("./sql/consulta_detalle_uclm.sql")
    params = {"anio": anio, "mes": mes}
    result = session.execute(text(query), params).fetchall()
    return [dict(r._mapping) for r in result]

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from datetime import datetime
import os



def parse_dates(fecha_inicio: str, fecha_fin: str) -> Tuple[datetime, datetime]:
    """
    Convierte las fechas de string a datetime con rango completo de día.

    - inicio: YYYY-MM-DD 00:00:00
    - fin: YYYY-MM-DD 23:59:59.999999

    Lanza un ValueError si el formato no es válido.
    """
    try:
        fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d") + timedelta(days=1) - timedelta(microseconds=1)
        return fecha_inicio_dt, fecha_fin_dt
    except ValueError:
        raise ValueError("Las fechas deben estar en formato YYYY-MM-DD")

def read_sql_file(file_path: str) -> str:
    """Lee una consulta SQL desde un archivo y la devuelve como un string."""
    with open(file_path, "r", encoding='utf-8') as file:
        return file.read()

@db_session
def execute_query(session, file_path: str, params: dict) -> List[Tuple]:
    """Ejecuta una consulta SQL desde un archivo con parámetros proporcionados."""
    query = read_sql_file(file_path)
    result = session.execute(text(query).params(**params)).fetchall()
    return result

def query_regla_negocio(
    cod_diagnostico_principal: str, 
    especialidad_profesional: str, 
    fecha_inicio: str, 
    fecha_fin: str
) -> pd.DataFrame:
    """Ejecuta consulta de reglas de negocio con filtros de diagnóstico y especialidad."""
    fecha_inicio_date, fecha_fin_date = parse_dates(fecha_inicio, fecha_fin)
    query_params = {
        "cod_diagnostico_principal": cod_diagnostico_principal,
        "especialidad_profesional": especialidad_profesional,
        "fecha_inicio": fecha_inicio_date,
        "fecha_fin": fecha_fin_date,
    }
    try:
        result = execute_query("./sql/consulta1.sql", query_params)
        if not result:
            return pd.DataFrame()
        df = pd.DataFrame(result, columns=[
            "id_licencia", "folio", "dias_reposo", "fecha_emision",
            "fecha_inicio_reposo", "especialidad_profesional", "cod_diagnostico_principal"
        ])
        return df
    except Exception as e:
        logger.error(f"Error ejecutando query_regla_negocio: {str(e)}")
        raise

@db_session
def update_propensity_score_licencias(session, results: pd.DataFrame, score_column: str, rn: int) -> None:
    """
    Actualiza la tabla ml.propensity_score con un lote de resultados.
    """
    if results.empty or score_column not in results.columns:
        logger.error(f"Datos vacíos o columna {score_column} no encontrada")
        return
    upsert_query = """
    INSERT INTO ml.propensity_score (id_lic, folio, rn, score)
    VALUES (:id_lic, :folio, :rn, :score)
    ON CONFLICT (id_lic, rn) DO UPDATE
    SET score = EXCLUDED.score
    """
    params_list = [
        {
            'id_lic': row['id_licencia'],
            'folio': row['folio'],
            'rn': rn,
            'score': row[score_column]
        }
        for _, row in results.iterrows()
    ]
    session.execute(text(upsert_query), params_list)
    successful_ids = [row['id_licencia'] for _, row in results.iterrows()]
    logger.info(f"Registros insertados exitosamente: {len(successful_ids)} IDs")

def query_masivo(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """Ejecuta consulta masiva de licencias en un rango de fechas."""
    fecha_inicio_date, fecha_fin_date = parse_dates(fecha_inicio, fecha_fin)
    query_params = {
        "fecha_inicio": fecha_inicio_date,
        "fecha_fin": fecha_fin_date,
    }
    try:
        result = execute_query("./sql/masivo.sql", query_params)
        if not result:
            return pd.DataFrame()
        df = pd.DataFrame(result, columns=[
            "id_licencia", "folio", "dias_reposo", "fecha_emision",
            "fecha_inicio_reposo", "especialidad_profesional", "cod_diagnostico_principal"
        ])
        return df
    except Exception as e:
        logger.error(f"Error ejecutando query_masivo: {str(e)}")
        raise

def query_score(fecha_inicio: str, fecha_fin: str) -> List[dict]:
    """Consulta resumen de propensity scores."""
    fecha_inicio_date, fecha_fin_date = parse_dates(fecha_inicio, fecha_fin)
    query_params = {
        "fecha_inicio": fecha_inicio_date,
        "fecha_fin": fecha_fin_date,
    }
    try:
        result = execute_query("./sql/propensy_score_resume.sql", query_params)
        if not result:
            return []
        return [
            {
                "fecha_emision": row[0],
                "rn": row[1],
                "cantidad_registros": row[2]
            }
            for row in result
        ]
    except Exception as e:
        logger.error(f"Error ejecutando query_score: {str(e)}")
        raise

def query_score_licencia(fecha_inicio: str, fecha_fin: str) -> List[dict]:
    """Consulta propensity scores por licencia."""
    fecha_inicio_date, fecha_fin_date = parse_dates(fecha_inicio, fecha_fin)
    query_params = {
        "fecha_inicio": fecha_inicio_date,
        "fecha_fin": fecha_fin_date,
    }
    try:
        result = execute_query("./sql/propensy_score_licencia.sql", query_params)
        if not result:
            return []
        agrupados = defaultdict(lambda: {"score": {}})
        for row in result:
            licencia = row[0]
            fecha_emision = row[1]
            rut_medico = row[2]
            dias_reposo = row[3]
            cod_diagnostico = row[4]
            especialidad_medico = row[5]
            rn = row[6]
            score = row[7]
            key = (licencia, fecha_emision, rut_medico, dias_reposo, cod_diagnostico, especialidad_medico)
            agrupados[key]["score"][f"rn_{rn}"] = score
            if "licencia" not in agrupados[key]:
                agrupados[key].update({
                    "licencia": licencia,
                    "fecha_emision": fecha_emision,
                    "rut_medico": rut_medico,
                    "dias_reposo": dias_reposo,
                    "cod_diagnostico": cod_diagnostico,
                    "especialidad_medico": especialidad_medico,
                })
        return list(agrupados.values())
    except Exception as e:
        logger.error(f"Error ejecutando query_score_licencia: {str(e)}")
        raise

def query_data_umbral(fecha: str, dias: int = 60, columna_entidad: str = "rut_medico") -> List[List]:
    """Ejecuta consulta de umbral y retorna resultados con tiempo de ejecución."""
    try:
        fecha_date = datetime.strptime(fecha, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("El formato de la fecha debe ser YYYY-MM-DD")
    query_params = {
        "fecha_inicio": fecha_date,
        "windows_days": dias,
    }
    result = execute_query("./sql/datos_umbral.sql", query_params)
    return result


@db_session
def clear_umbral_data_table(session) -> None:
    """
    Vacía la tabla ml.umbral_data.
    """
    try:
        session.execute(text("TRUNCATE TABLE ml.umbral_data;"))
        session.commit()
        logger.info("Tabla ml.umbral_data vaciada exitosamente.")
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Error al vaciar la tabla ml.umbral_data: {e}")
        raise

@db_session
def manage_umbral_status(
    session,
    request_hash: str,
    fecha: str,
    dias: int,
    entidad: str,
    status: str
) -> dict:
    """
    Inserta o actualiza el estado en la tabla ml.umbral_data y devuelve el registro.
    """
    clear_umbral_data_table(session)
    upsert_query = """
    INSERT INTO ml.umbral_data (hash, fecha, dias, entidad, estado, created_at)
    VALUES (:hash, :fecha, :dias, :entidad, :estado, :created_at)
    ON CONFLICT (hash) DO UPDATE
    SET estado = EXCLUDED.estado,
        created_at = EXCLUDED.created_at
    RETURNING hash, fecha, dias, entidad, estado, created_at
    """
    params = {
        "hash": request_hash,
        "fecha": fecha,
        "dias": dias,
        "entidad": entidad,
        "estado": status,
        "created_at": datetime.now()
    }
    result = session.execute(text(upsert_query), params).fetchone()
    if not result:
        raise ValueError("No se pudo registrar o actualizar el estado en ml.umbral_data")
    return {
        "status": result.estado,
        "request_hash": result.hash,
        "fecha": result.fecha,
        "dias": result.dias,
        "entidad": result.entidad,
        "created_at": result.created_at.isoformat()
    }

@db_session
def get_umbral_status(session, request_hash: str) -> dict:
    """Consulta el estado de un request_hash en la tabla ml.umbral_data."""
    query = """
    SELECT hash, fecha, dias, entidad, estado, created_at
    FROM ml.umbral_data
    WHERE hash = :hash
    """
    result = session.execute(text(query), {"hash": request_hash}).fetchone()
    if not result:
        return {"status": "not_found", "message": "Request hash not found"}
    return {
        "status": result.estado,
        "request_hash": result.hash,
        "fecha": result.fecha,
        "dias": result.dias,
        "entidad": result.entidad,
        "created_at": result.created_at.isoformat()
    }

@db_session
def insert_umbrales(session, results: pd.DataFrame, fecha: str, dias: int, columna_entidad: str) -> None:
    """
    Inserta los datos procesados de umbrales en la tabla ml.umbrales.
    """
    if results.empty:
        logger.warning("DataFrame vacío, no se insertan datos en ml.umbrales")
        return
    results['fecha'] = fecha
    results['dias'] = dias
    results['columna_entidad'] = columna_entidad
    if 'id_licencia' in results.columns:
        results = results.rename(columns={'id_licencia': 'id_lic'})
    expected_columns = [
        'id_lic', 'folio', 'fecha', 'dias', 'columna_entidad',
        'dias_reposo', 'fecha_emision', 'fecha_inicio_reposo',
        'especialidad_profesional', 'cod_diagnostico_principal',
        'rut_medico', 'rut_trabajador', 'marca_otorgamiento',
        'frecuencia_medico_30D', 'frecuencia_medico_15D', 'frecuencia_medico_7D',
        'frecuencia_J_30D_medico', 'frecuencia_F_30D_medico', 'frecuencia_M_30D_medico',
        'n_remotas_30D', 'n_presenciales_30D',
        'score_frecuencia_medico_7D', 'score_frecuencia_medico_15D',
        'score_frecuencia_medico_30D', 'score_frecuencia_F_30D_medico',
        'score_frecuencia_J_30D_medico', 'score_frecuencia_M_30D_medico',
        'score_n_remotas_30D', 'score_n_presenciales_30D'
    ]
    for col in expected_columns:
        if col not in results.columns:
            if 'score_' in col:
                results[col] = 0.0
            else:
                logger.warning(f"Columna {col} no encontrada en DataFrame, se seteará a NULL")
                results[col] = None
    upsert_query = """
    INSERT INTO ml.umbrales (
        id_lic, folio, fecha, dias, columna_entidad,
        dias_reposo, fecha_emision, fecha_inicio_reposo,
        especialidad_profesional, cod_diagnostico_principal,
        rut_medico, rut_trabajador, marca_otorgamiento,
        frecuencia_medico_30D, frecuencia_medico_15D, frecuencia_medico_7D,
        frecuencia_J_30D_medico, frecuencia_F_30D_medico, frecuencia_M_30D_medico,
        n_remotas_30D, n_presenciales_30D,
        score_frecuencia_medico_7D, score_frecuencia_medico_15D,
        score_frecuencia_medico_30D, score_frecuencia_F_30D_medico,
        score_frecuencia_J_30D_medico, score_frecuencia_M_30D_medico,
        score_n_remotas_30D, score_n_presenciales_30D
    ) VALUES (
        :id_lic, :folio, :fecha, :dias, :columna_entidad,
        :dias_reposo, :fecha_emision, :fecha_inicio_reposo,
        :especialidad_profesional, :cod_diagnostico_principal,
        :rut_medico, :rut_trabajador, :marca_otorgamiento,
        :frecuencia_medico_30D, :frecuencia_medico_15D, :frecuencia_medico_7D,
        :frecuencia_J_30D_medico, :frecuencia_F_30D_medico, :frecuencia_M_30D_medico,
        :n_remotas_30D, :n_presenciales_30D,
        :score_frecuencia_medico_7D, :score_frecuencia_medico_15D,
        :score_frecuencia_medico_30D, :score_frecuencia_F_30D_medico,
        :score_frecuencia_J_30D_medico, :score_frecuencia_M_30D_medico,
        :score_n_remotas_30D, :score_n_presenciales_30D
    )
    ON CONFLICT (id_lic, dias, columna_entidad) DO NOTHING
    """
    params_list = [
        {col: row.get(col, None) for col in expected_columns}
        for _, row in results.iterrows()
    ]
    session.execute(text(upsert_query), params_list)
    logger.info(f"Insertados/actualizados {len(params_list)} registros en ml.umbrales")

@db_session
def insert_anomalias(session, results: pd.DataFrame) -> None:
    """
    Inserta los datos procesados de anomalías en la tabla ml.anomalias.
    Usa INSERT con ON CONFLICT DO NOTHING para manejar duplicados (basado en id_lic).
    """
    if results.empty:
        logger.warning("DataFrame vacío, no se insertan datos en ml.anomalias")
        return
    if 'id_licencia' in results.columns:
        results = results.rename(columns={'id_licencia': 'id_lic'})
    expected_columns = [
        "id_lic", "rut_medico", "rut_trabajador", "rut_empleador", "dias_reposo",
        "edad_trabajador", "hora_emision", "dia_codificado",
        "calidad_trabajador_independiente", "calidad_trabajador_dependiente_privado",
        "calidad_trabajador_publico_afecto", "calidad_trabajador_publico_no_afecto",
        "recencia_trabajador", "frecuencia_trabajador_60d", "frecuencia_trabajador_40d",
        "frecuencia_trabajador_20d", "reposo_trabajador_60d", "reposo_trabajador_40d",
        "reposo_trabajador_20d", "n_medicos_distintos_xtrabajador_60d",
        "n_empleadores_distintos_xtrabajador_60d", "desviacion_reposo_trabajador_60d",
        "recencia_medico", "frecuencia_medico_30d", "frecuencia_medico_15d",
        "frecuencia_medico_7d", "reposo_medico_30d", "reposo_medico_15d",
        "reposo_medico_7d", "licencias_20_min", "licencias_40_min", "licencias_60_min",
        "max_licencias_dia_30d", "frecuencia_j_30d_medico", "frecuencia_f_30d_medico",
        "frecuencia_m_30d_medico", "max_rest_days_30d", "diferencia_dias",
        "licencias_despues_umbral", "n_trabajadores_distintos_xmedico_60d",
        "n_empleadores_distintos_xmedico_60d", "hhi_empleadores_por_medico_60d",
        "n_remotas_30d", "n_presenciales_30d", "recencia_empleador",
        "frecuencia_empleador_60d", "frecuencia_empleador_40d", "frecuencia_empleador_20d",
        "reposo_empleador_60d", "reposo_empleador_40d", "reposo_empleador_20d",
        "n_trabajadores_distintos_xempleador_60d", "n_medicos_distintos_xempleador_60d",
        "frecuencia_j_30d_empleador", "frecuencia_f_30d_empleador", "frecuencia_m_30d_empleador",
        "historial_trabajador_medico", "historial_empleador_medico", "ponderado_medico_trabajador",
        "anomaly_score", "propensity_score_iforest"
    ]
    for col in expected_columns:
        if col not in results.columns:
            results[col] = None
    upsert_query = f"""
    INSERT INTO ml.anomalias (
        {", ".join(expected_columns)}
    ) VALUES (
        {", ".join([f":{col}" for col in expected_columns])}
    )
    ON CONFLICT (id_lic) DO NOTHING
    """
    params_list = [
        {col: row.get(col, None) for col in expected_columns}
        for _, row in results.iterrows()
    ]
    session.execute(text(upsert_query), params_list)
    logger.info(f"Insertados/actualizados {len(params_list)} registros en ml.anomalias")

def consulta_licencia(where_query: ConsultaLicenciaRequest) -> pd.DataFrame:
    """
    Ejecuta la consulta de licencias con filtros opcionales, incluyendo columnas de ml.anomalias no redundantes.
    """
    query_path = "./sql/consulta_licencia.sql"
    fecha_unica = where_query.fecha
    fecha_inicio = where_query.fecha_inicio
    fecha_fin = where_query.fecha_fin
    if (fecha_inicio and not fecha_fin) or (fecha_fin and not fecha_inicio):
        raise ValueError("Debe especificar tanto fecha_inicio como fecha_fin o ninguna")
    if fecha_inicio and fecha_fin:
        fecha_inicio, fecha_fin = parse_dates(where_query.fecha_inicio, where_query.fecha_fin)
    query_params = {
        "id_lic": where_query.id_lic,
        "rut_trabajador": where_query.rut_trabajador,
        "rut_medico": where_query.rut_medico,
        "rut_empleador": where_query.rut_empleador,
        "folio": where_query.folio,
        "fecha_unica": fecha_unica,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "cod_diagnostico": where_query.cod_diagnostico,
        "especialidad_medico": where_query.especialidad_medico,
    }
    try:
        result = execute_query(query_path, query_params)
        if not result:
            return pd.DataFrame()
        df = pd.DataFrame(result, columns=[
            "id_lic", "operador", "ccaf", "entidad_pagadora", "folio",
            "fecha_emision", "empleador_adscrito", "codigo_interno_prestador",
            "comuna_prestador", "fecha_ultimo_estado", "ultimo_estado",
            "rut_trabajador", "sexo_trabajador", "edad_trabajador",
            "tipo_reposo", "dias_reposo", "fecha_inicio_reposo",
            "comuna_reposo", "tipo_licencia", "rut_medico",
            "tipo_licencia_pronunciamiento", "codigo_continuacion_pronunciamiento",
            "dias_autorizados_pronunciamiento", "codigo_diagnostico_pronunciamiento",
            "codigo_autorizacion_pronunciamiento", "causa_rechazo_pronunciamiento",
            "tipo_reposo_pronunciamiento", "derecho_a_subsidio_pronunciamiento",
            "rut_empleador", "calidad_trabajador", "actividad_laboral_trabajador",
            "ocupacion", "entidad_pagadora_zona_c", "fecha_recepcion_empleador",
            "regimen_previsional", "entidad_pagadora_subsidio", "comuna_laboral",
            "comuna_uso_compin", "cantidad_de_pronunciamientos", "cantidad_de_zonas_d",
            "secuencia_estados", "cod_diagnostico_principal", "cod_diagnostico_secundario",
            "periodo", "marca_otorgamiento", "cod_diagnostico", "especialidad_medico",
            "rn1", "rn2", "score_frecuencia_medico_7d", "score_frecuencia_medico_15d",
            "score_frecuencia_medico_30d", "score_frecuencia_f_30d_medico",
            "score_frecuencia_j_30d_medico", "score_frecuencia_m_30d_medico",
            "score_n_remotas_30d", "score_n_presenciales_30d",
            # Columnas de ml.anomalias (solo las no redundantes)
            "anomalias_id", "anomalias_hora_emision", "anomalias_dia_codificado",
            "anomalias_calidad_trabajador_independiente", "anomalias_calidad_trabajador_dependiente_privado",
            "anomalias_calidad_trabajador_publico_afecto", "anomalias_calidad_trabajador_publico_no_afecto",
            "anomalias_recencia_trabajador", "anomalias_frecuencia_trabajador_60d",
            "anomalias_frecuencia_trabajador_40d", "anomalias_frecuencia_trabajador_20d",
            "anomalias_reposo_trabajador_60d", "anomalias_reposo_trabajador_40d",
            "anomalias_reposo_trabajador_20d", "anomalias_n_medicos_distintos_xtrabajador_60d",
            "anomalias_n_empleadores_distintos_xtrabajador_60d", "anomalias_desviacion_reposo_trabajador_60d",
            "anomalias_recencia_medico", "anomalias_reposo_medico_30d",
            "anomalias_reposo_medico_15d", "anomalias_reposo_medico_7d",
            "anomalias_licencias_20_min", "anomalias_licencias_40_min",
            "anomalias_licencias_60_min", "anomalias_max_licencias_dia_30d",
            "anomalias_max_rest_days_30d", "anomalias_diferencia_dias",
            "anomalias_licencias_despues_umbral", "anomalias_n_trabajadores_distintos_xmedico_60d",
            "anomalias_n_empleadores_distintos_xmedico_60d", "anomalias_hhi_empleadores_por_medico_60d",
            "anomalias_recencia_empleador", "anomalias_frecuencia_empleador_60d",
            "anomalias_frecuencia_empleador_40d", "anomalias_frecuencia_empleador_20d",
            "anomalias_reposo_empleador_60d", "anomalias_reposo_empleador_40d",
            "anomalias_reposo_empleador_20d", "anomalias_n_trabajadores_distintos_xempleador_60d",
            "anomalias_n_medicos_distintos_xempleador_60d", "anomalias_frecuencia_j_30d_empleador",
            "anomalias_frecuencia_f_30d_empleador", "anomalias_frecuencia_m_30d_empleador",
            "anomalias_historial_trabajador_medico", "anomalias_historial_empleador_medico",
            "anomalias_ponderado_medico_trabajador", "anomalias_anomaly_score",
            "anomalias_propensity_score_iforest", "anomalias_fecha_creacion"
        ])
        return df
    except pd.errors.ParserError as e:
        logger.error(f"Error en el parseo del DataFrame: columnas no coinciden: {str(e)}")
        raise ValueError(f"Error en el parseo del DataFrame: {str(e)}")
    except Exception as e:
        logger.error(f"Error ejecutando consulta_licencia: {str(e)}")
        raise



@db_session
def guardar_semaforo(session, data: dict) -> dict:
    """
    Inserta o actualiza un resultado del semáforo en ml.semaforo_resultados.
    Si existe (rut_medico + rango), lo actualiza; de lo contrario, lo inserta.
    """
    query = read_sql_file("./sql/guardar_semaforo.sql")
    params = {
        "rut_medico": data.get("rut_medico"),
        "n_lic": data.get("n_lic", 0),
        "rn": data.get("rn", 0),
        "rango": data.get("rango"),
        "um": data.get("um", 0),
        "an": data.get("an", 0),
        "smf_rn": data.get("smf_rn", 0.0),
        "smf_um": data.get("smf_um", 0.0),
        "smf_an": data.get("smf_an", 0.0),
        "created_at": datetime.now()
    }
    result = session.execute(text(query), params).fetchone()
    if not result:
        raise ValueError("No se pudo guardar el registro en ml.semaforo_resultados")
    return dict(result._mapping)


@db_session
def consulta_semaforo(session, rango: str = None, rut_medico: str = None) -> list[dict]:
    """
    Consulta resultados de semáforo filtrando opcionalmente por rango y/o rut_medico.
    """
    query = read_sql_file("./sql/consulta_semaforo.sql")
    params = {"rango": rango, "rut_medico": rut_medico}
    result = session.execute(text(query), params).fetchall()
    return [dict(r._mapping) for r in result]

# fmateluna : Se crea esta nueva funcion para la consulta de reclamos
@db_session
def consulta_semaforo_reclamos(session, anio: int, mes: int, rut_medico: Optional[str] = None) -> list[dict]:
    """
    Consulta licencias y scores para el proceso de reclamos.
    """
    query = read_sql_file("./sql/consulta_semaforo_reclamos.sql")
    # Se agrega el parámetro opcional rut_medico a la consulta
    params = {"anio": anio, "mes": mes, "rut_medico": rut_medico}
    try:
        result = session.execute(text(query), params).fetchall()
        return [dict(r._mapping) for r in result]
    except Exception as e:
        logger.error(f"Error de base de datos en consulta_semaforo_reclamos: {e}")
        raise

# fmateluna : Se agrega rut_medico como opcional
@db_session
def consulta_licencias_periodo(session, anio: int, mes: int, rut_medico: Optional[str] = None) -> list[dict]:
    """
    Retorna un DataFrame con las licencias filtradas por año y mes.
    """
    query = read_sql_file("./sql/consulta_licencias_periodo.sql")
    params = {"anio": str(anio), "mes": f"{mes:02d}", "rut_medico": rut_medico}
    result = session.execute(text(query), params).fetchall()
    return [dict(r._mapping) for r in result]