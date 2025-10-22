import pandas as pd
import numpy as np

from core.repo_anomalias.run_anomalias import exec_anomalias
from core.services import insert_anomalias
from core.utils.license_processing import count_licenses_by_entity, count_licenses_by_otorgamiento, count_licenses_by_diagnosis

# Función que calcula la cantidad de días de reposo otorgados por una entidad (médico, trabajador, empleador) en un periodo de tiempo definido. MUY OPTIMIZADA.
def count_dias_reposo_by_entity(df, entity_col='rut_medico', window_days=30):
    df_sorted = df.sort_values(by=[entity_col, 'fecha_emision'])
    fecha = df_sorted['fecha_emision'].values
    entity = df_sorted[entity_col].values
    reposo = df_sorted['dias_reposo'].values
    index = df_sorted.index.values

    result = np.zeros(len(df_sorted), dtype=int)
    pos = 0

    while pos < len(df_sorted):
        curr_entity = entity[pos]
        start = pos
        while pos < len(df_sorted) and entity[pos] == curr_entity:
            pos += 1
        end = pos

        fechas_entidad = fecha[start:end]
        dias = (fechas_entidad - fechas_entidad[0]) / np.timedelta64(1, 'D')
        dias = dias.astype(np.int32)

        # Acumulado de días de reposo
        cumsum_reposo = np.cumsum(reposo[start:end])
        left_idxs = np.searchsorted(dias, dias - window_days, side='left')

        # Calculamos la suma usando diferencias de cumsum
        total = cumsum_reposo - np.where(left_idxs > 0, cumsum_reposo[left_idxs - 1], 0)

        # Excluir el día actual
        total -= reposo[start:end]

        result[start:end] = total

    return pd.Series(result, index=df_sorted.index).reindex(df.index)

# Función que calcula el número de entidades distintas en una ventana de tiempo definida agrupadas por una entidad de referencia.
def count_distinct_entities(df, entidad_referencia, entidad_conteo, window_days=30):
    """
    Calcula el número de entidades distintas (por ejemplo, médicos, trabajadores) en una ventana de tiempo definida,
    agrupadas por una entidad de referencia (ej. trabajador o empleador).

    Parámetros:
        df (pd.DataFrame): DataFrame que contiene 'fecha_emision' y las columnas de agrupación y conteo.
        entidad_referencia (str): Columna por la cual se agrupará el historial (ej. 'rut_trabajador', 'rut_empleador').
        entidad_conteo (str): Columna cuyos valores distintos se contarán (ej. 'rut_medico', 'rut_trabajador').
        window_days (int): Ventana de tiempo hacia atrás (en días) para contar las entidades.

    Retorna:
        pd.Series: Serie con los conteos para cada fila, alineada con el índice original de df.
    """
    df_sorted = df.sort_values(by=[entidad_referencia, 'fecha_emision']).copy()
    original_index = df_sorted.index

    df_sorted['dias'] = (df_sorted['fecha_emision'] - df_sorted['fecha_emision'].min()).dt.days
    resultados = pd.Series(0, index=original_index, dtype=int)

    for clave, grupo in df_sorted.groupby(entidad_referencia):
        dias = grupo['dias'].values
        valores = grupo[entidad_conteo].values
        indices = grupo.index.values

        for i in range(len(dias)):
            start = dias[i] - window_days
            filtro = (dias >= start) & (dias < dias[i])
            resultados.at[indices[i]] = len(set(valores[filtro]))

    return resultados.reindex(df.index)

# Función que cálcula la desviación en los días de reposo recibidos por un trabajador en una ventana de tiempo definida.
def desviacion_reposo_trabajador(df, window_days=30):
    """
    Calcula la desviación estándar de los días de reposo que ha recibido un trabajador en una ventana de tiempo.

    Parámetros:
        df (pd.DataFrame): Debe contener columnas «rut_trabajador», «fecha_emision» y «dias_reposo».
        window_days (int): Tamaño de la ventana en días. Por defecto, 30.

    Retorna:
        pd.Series: Desviación estándar de los días de reposo para cada licencia, alineada con índice original.
    """
    df_sorted = df.sort_values(by=['rut_trabajador', 'fecha_emision']).copy()
    original_index = df_sorted.index

    df_sorted['dias'] = (df_sorted['fecha_emision'] - df_sorted['fecha_emision'].min()).dt.days
    resultados = pd.Series(0.0, index=original_index, dtype=float)

    for rut, group in df_sorted.groupby('rut_trabajador'):
        dias = group['dias'].values
        reposos = group['dias_reposo'].values
        idxs = group.index.values

        for i in range(len(dias)):
            start = dias[i] - window_days
            ventana_reposo = reposos[(dias >= start) & (dias < dias[i])]
            if len(ventana_reposo) > 1:
                resultados.at[idxs[i]] = np.std(ventana_reposo)
            else:
                resultados.at[idxs[i]] = 0.0  # o np.nan si prefieres

    return resultados.reindex(df.index)

# Función que calcula el máximo número de licencias médicas emitidas por un médico en un periodo de tiempo determinado (días, semanas).
def max_licenses_per_time_period(df, window_days=30, window_type="day"):
    """
    Calcula el máximo número de licencias médicas emitidas por un médico en un periodo de tiempo dentro de los
    últimos `window_days` previos a la fecha de emisión de cada licencia médica. El periodo puede ser en días o semanas.

    Parameters:
        df (pd.DataFrame): DataFrame que contiene las columnas «rut_medico» y «fecha_emision».
        window_days (int): Duración de la ventana temporal en días. Por defecto, 30.
        window_type (str): Tipo de ventana temporal para calcular el máximo ('day' o 'week').

    Returns:
        pd.Series: Serie con el máximo número de licencias emitidas, alineada con el índice original del DataFrame.
    """
    df_sorted = df.sort_values(by=['rut_medico', 'fecha_emision']).copy()
    original_index = df_sorted.index
    min_fecha = df_sorted['fecha_emision'].min()
    df_sorted['dias'] = (df_sorted['fecha_emision'] - min_fecha).dt.days

    results = pd.Series(0, index=original_index)

    for rut_medico, group in df_sorted.groupby('rut_medico'):
        dias = group['dias'].values
        indices = group.index.values  # Índices originales

        # Contar licencias por día
        unique_days, daily_counts = np.unique(dias, return_counts=True)
        day_dict = dict(zip(unique_days, daily_counts))

        start_indices = np.searchsorted(dias, dias - window_days, side='left')

        if window_type == "day":
            for i, idx in enumerate(indices):
                start_idx = start_indices[i]
                max_day = max([day_dict.get(d, 0) for d in dias[start_idx:i+1]], default=0)
                results.at[idx] = max_day

        elif window_type == "week":
            for i, idx in enumerate(indices):
                start_idx = start_indices[i]
                max_week = 0
                for start_day in range(dias[start_idx], dias[i] - 6):
                    week_sum = sum(day_dict.get(d, 0) for d in range(start_day, start_day + 7))
                    max_week = max(max_week, week_sum)
                results.at[idx] = max_week

    return results.reindex(df.index)

# Función que calcula el máximo de días de reposo otorgados en un tiempo definido.
def max_rest_days_per_time_period(df, window_days=30, window_type="day"):
    """
    Cálculo optimizado del máximo de días de reposo por periodo de tiempo, alineado con el índice original.

    Parámetros:
        df (pd.DataFrame): Debe contener columnas 'rut_medico', 'fecha_emision' y 'dias_reposo'.
        window_days (int): Duración de la ventana temporal en días (por defecto 30).
        window_type (str): 'day' para máximo diario, 'week' para máximo semanal.

    Retorna:
        pd.Series: Máximo de días de reposo en la ventana, alineado con el índice original.
    """
    df_sorted = df.sort_values(by=['rut_medico', 'fecha_emision']).copy()
    original_index = df_sorted.index
    min_fecha = df_sorted['fecha_emision'].min()
    df_sorted['dias'] = (df_sorted['fecha_emision'] - min_fecha).dt.days

    results = pd.Series(0, index=original_index, dtype=int)

    for rut_medico, group in df_sorted.groupby('rut_medico'):
        dias = group['dias'].values
        dias_reposo = group['dias_reposo'].values
        indices = group.index.values  # Índices originales

        # Sumar días de reposo por cada día único
        unique_days, inverse_idx = np.unique(dias, return_inverse=True)
        reposo_por_dia = np.zeros(len(unique_days), dtype=int)
        np.add.at(reposo_por_dia, inverse_idx, dias_reposo)
        day_to_reposo = dict(zip(unique_days, reposo_por_dia))

        if window_type == "day":
            for i, idx in enumerate(indices):
                dia_actual = dias[i]
                inicio_ventana = dia_actual - window_days
                dias_en_ventana = unique_days[(unique_days >= inicio_ventana) & (unique_days <= dia_actual)]
                max_reposo = max((day_to_reposo[d] for d in dias_en_ventana), default=0)
                results.at[idx] = max_reposo

        elif window_type == "week":
            for i, idx in enumerate(indices):
                dia_actual = dias[i]
                inicio_ventana = dia_actual - window_days
                dias_en_ventana = unique_days[(unique_days >= inicio_ventana) & (unique_days <= dia_actual)]
                max_reposo = 0
                for start_day in dias_en_ventana:
                    suma_semana = sum(day_to_reposo.get(d, 0) for d in range(start_day, start_day + 7))
                    if suma_semana > max_reposo:
                        max_reposo = suma_semana
                results.at[idx] = max_reposo

    return results.reindex(df.index)

# Función que cálcula los días que el médico tardó en alcanzar el umbral de licencias médicas y cuántas licencias emitió después de eso.
def calcular_dias_para_umbral(df, umbral, window_days=30):
    """
    Calcula para cada licencia médica:
    - Cuántos días tardó el médico en alcanzar el umbral dentro de la ventana de tiempo (`window_days`).
    - Cuántas licencias adicionales emitió después de alcanzar ese umbral.

    Parámetros:
        df (pd.DataFrame): DataFrame con columnas 'rut_medico' y 'fecha_emision'.
        umbral (int): Número de licencias que define el umbral a alcanzar.
        window_days (int): Ventana de tiempo en días para el cálculo. Por defecto, 30 días.

    Retorna:
        pd.DataFrame: DataFrame original con columnas adicionales:
            - 'diferencia_dias': Días hasta alcanzar el umbral dentro de la ventana.
            - 'licencias_despues_umbral': Licencias emitidas después de alcanzar el umbral.
    """
    df_sorted = df.sort_values(by=['rut_medico', 'fecha_emision']).copy()
    original_index = df_sorted.index

    df_sorted['dias'] = (df_sorted['fecha_emision'] - df_sorted['fecha_emision'].min()).dt.days

    diferencia_dias = pd.Series(window_days + 1, index=original_index, dtype=int)  # valor por defecto
    licencias_despues_umbral = pd.Series(0, index=original_index, dtype=int)

    for rut_medico, group in df_sorted.groupby('rut_medico'):
        dias = group['dias'].values
        indices = group.index.values  # índices originales

        for i in range(len(dias)):
            start_date = dias[i] - window_days
            licencias_window = dias[(dias >= start_date) & (dias <= dias[i])]

            if len(licencias_window) >= umbral:
                fecha_umbral = licencias_window[umbral - 1]  # cuando se alcanzó el umbral
                diferencia_dias.at[indices[i]] = fecha_umbral - dias[i] + window_days

                licencias_despues_umbral.at[indices[i]] = np.sum(dias > fecha_umbral)

    df_result = df.copy()
    df_result['diferencia_dias'] = diferencia_dias.reindex(df_result.index)
    df_result['licencias_despues_umbral'] = licencias_despues_umbral.reindex(df_result.index)
    return df_result

# Función que calcula el índice HHI por médico dentro de una ventana de tiempo hacia atrás para cada licencia.
def calcular_hhi_empleadores(df, window_days=60):
    """
    Calcula el índice HHI por médico dentro de una ventana de tiempo hacia atrás para cada licencia.

    Parámetros:
        df (pd.DataFrame): Debe contener 'rut_medico', 'rut_empleador' y 'fecha_emision'.
        window_days (int): Número de días hacia atrás desde cada licencia.

    Retorna:
        pd.Series: Serie con el índice HHI para cada licencia, alineada con índice original.
    """
    df_sorted = df.sort_values(by=['rut_medico', 'fecha_emision']).copy()
    original_index = df_sorted.index

    hhi_resultados = pd.Series(np.nan, index=original_index, dtype=float)

    for rut_medico, grupo in df_sorted.groupby('rut_medico'):
        fechas = grupo['fecha_emision'].values
        empleadores = grupo['rut_empleador'].astype(str).fillna('MISSING_EMPLOYER').values
        idxs = grupo.index.values

        for i in range(len(grupo)):
            fecha_actual = fechas[i]
            inicio_ventana = fecha_actual - np.timedelta64(window_days, 'D')

            mask_ventana = (fechas < fecha_actual) & (fechas >= inicio_ventana)
            empleadores_ventana = empleadores[mask_ventana]
            empleadores_filtrados = empleadores_ventana[empleadores_ventana != 'MISSING_EMPLOYER']

            if len(empleadores_filtrados) == 0:
                hhi_resultados.at[idxs[i]] = np.nan  # o 0, según prefieras
                continue

            _, counts = np.unique(empleadores_filtrados, return_counts=True)
            proporciones = counts / counts.sum()
            hhi = np.sum(proporciones**2)
            hhi_resultados.at[idxs[i]] = hhi

    return hhi_resultados.reindex(df.index)

# Función que calcula la cantidad de licencias emitidas por el médico en los últimos 20, 40 y 60 minutos. FUNCIONA RÁPIDO
def count_licenses_numpy_minutes(df, window_minutes=[20, 40, 60]):
    """
    Calcula el número de licencias emitidas por cada médico («rut_medico») en ventanas de tiempo
    especificadas (en minutos), conservando el índice original del DataFrame.

    Parámetros:
        df (pd.DataFrame): DataFrame con columnas 'rut_medico' y 'fecha_emision'.
        window_minutes (list): Lista de duraciones de ventanas temporales en minutos (ej: [20, 40, 60]).

    Retorna:
        dict: Diccionario donde cada clave es 'licencias_X_min' y cada valor es una pd.Series alineada con el índice original.
    """
    df_sorted = df.sort_values(by=['rut_medico', 'fecha_emision']).copy()
    original_index = df_sorted.index

    timestamps = df_sorted['fecha_emision'].astype(np.int64) // 10**9
    rut_medicos = df_sorted['rut_medico'].values

    results = {f'licencias_{w}_min': pd.Series(0, index=original_index) for w in window_minutes}

    unique_ruts, rut_starts, rut_counts = np.unique(rut_medicos, return_index=True, return_counts=True)
    rut_ends = rut_starts + rut_counts

    for rut_start, rut_end in zip(rut_starts, rut_ends):
        group_idx = original_index[rut_start:rut_end]
        group_timestamps = timestamps[rut_start:rut_end]
        n = len(group_timestamps)

        for w in window_minutes:
            window_seconds = w * 60
            start_indices = np.searchsorted(group_timestamps, group_timestamps - window_seconds, side='left')
            counts = np.arange(n) - start_indices + 1
            results[f'licencias_{w}_min'].loc[group_idx] = counts

    # Reindex para asegurar que el resultado final esté en el orden original del df
    return {k: v.reindex(df.index) for k, v in results.items()}

def count_dias_reposo_by_empleador(df, window_days=30):
    df = df.copy()

    # Asegurar formato datetime
    df['fecha_emision'] = pd.to_datetime(df['fecha_emision'], errors='coerce')

    # Filas válidas (fecha_emision y rut_empleador no NaN)
    valid_mask = df['fecha_emision'].notna() & df['rut_empleador'].notna()
    df_valid = df.loc[valid_mask].copy()

    # Ordenar por empleador y fecha
    df_valid.sort_values(by=['rut_empleador', 'fecha_emision'], inplace=True)

    fechas = df_valid['fecha_emision'].values.astype('datetime64[D]').astype('int32')
    empleadores = df_valid['rut_empleador'].values
    dias_reposo = df_valid['dias_reposo'].values

    result = np.full(len(df_valid), np.nan)

    unique_emp, start_idx, counts = np.unique(empleadores, return_index=True, return_counts=True)

    for i in range(len(unique_emp)):
        start = start_idx[i]
        end = start + counts[i]

        fechas_emp = fechas[start:end]
        dias_emp = dias_reposo[start:end]

        # Cumsum para sumas rápidas
        cumsum = np.cumsum(dias_emp)

        # Para cada fecha, encontrar ventana izquierda con búsqueda binaria
        left = np.searchsorted(fechas_emp, fechas_emp - window_days, side='left')

        # Sumar días en ventana (excluyendo día actual)
        total = cumsum - np.where(left > 0, cumsum[left - 1], 0) - dias_emp

        result[start:end] = total

    # Resultado con índice original y NaN en posiciones inválidas
    full_result = pd.Series(np.nan, index=df.index)
    full_result.loc[df_valid.index] = result

    return full_result

def count_licenses_by_empleador(df, window_days=30):
    df = df.copy()

    # Asegurar formato datetime
    df['fecha_emision'] = pd.to_datetime(df['fecha_emision'], errors='coerce')

    # Identificar filas válidas (sin NaN en fecha_emision ni rut_empleador)
    valid_mask = df['fecha_emision'].notna() & df['rut_empleador'].notna()
    df_valid = df.loc[valid_mask].copy()

    # Ordenar por empleador y fecha
    df_valid.sort_values(by=['rut_empleador', 'fecha_emision'], inplace=True)

    fechas = df_valid['fecha_emision'].values.astype('datetime64[D]').astype('int32')
    empleadores = df_valid['rut_empleador'].values

    result = np.full(len(df_valid), np.nan)

    unique_emp, start_idx, counts = np.unique(empleadores, return_index=True, return_counts=True)

    for emp_idx in range(len(unique_emp)):
        start = start_idx[emp_idx]
        end = start + counts[emp_idx]
        fechas_emp = fechas[start:end]

        left = np.searchsorted(fechas_emp, fechas_emp - window_days, side='left')
        result[start:end] = np.arange(end - start) - left

    # Crear una Serie con el índice original y NaNs en las posiciones no válidas
    full_result = pd.Series(np.nan, index=df.index)
    full_result.loc[df_valid.index] = result

    return full_result

def calcular_anomalias(df_licencias: pd.DataFrame):

    # Filtros iniciales sugeridos
    df_licencias = df_licencias[df_licencias['dias_reposo'] <= 365]
    df_licencias = df_licencias[~df_licencias['cod_diagnostico_principal'].isin(['U07.1', 'U07.2'])]
    df_licencias['fecha_emision'] = pd.to_datetime(df_licencias['fecha_emision'], errors='coerce')
    df_licencias = df_licencias.sort_values(by=['rut_medico', 'rut_trabajador', 'fecha_emision']).reset_index(drop=True)

    """
    df_licencias['n_trabajadores_reportados'] = df_licencias['n_trabajadores_reportados'] + 1

    trabajadores_por_empleador = df_licencias.groupby('rut_empleador')['rut_trabajador'].nunique().reset_index()
    trabajadores_por_empleador.rename(columns={'rut_trabajador': 'n_trabajadores_observados'}, inplace=True)
    df_licencias = df_licencias.merge(trabajadores_por_empleador, on='rut_empleador', how='left')
    df_licencias['n_trabajadores'] = df_licencias[['n_trabajadores_reportados', 'n_trabajadores_observados']].max(axis=1)
    """
    #########################################################################################################################
    # Atributos de la licencia
    #########################################################################################################################
    # Hora de emisión de la licencia médica
    df_licencias['hora_emision'] = df_licencias['fecha_emision'].dt.hour

    # Día codificado de emisión de la licencia médica (0-6, lunes a domingo)
    df_licencias['dia_codificado'] = df_licencias['fecha_emision'].dt.weekday

    #########################################################################################################################
    # Atributos del trabajador
    #########################################################################################################################
    # edad del trabajador relacionado a la emisión de la licencia médica.

    # Calidad del trabajador al que se le emite la licencia médica (dependiente o independiente)
    df_licencias = pd.get_dummies(df_licencias, columns=['calidad_trabajador'], prefix='calidad', dtype=int)

    # Calculamos la recencia del trabajador asociado a la licencia médica.
    df_licencias = df_licencias.sort_values(by=['rut_trabajador', 'fecha_emision'])
    df_licencias['recencia_trabajador'] = df_licencias.groupby('rut_trabajador')['fecha_emision'].diff().dt.total_seconds().fillna(2628002) / 60 # 1 mes en minutos

    # Calculamos la frecuencia de los últimos 60 días del trabajador asociado a la licencia médica.
    df_licencias['frecuencia_trabajador_60D'] = count_licenses_by_entity(df_licencias, entity_col='rut_trabajador', window_days=60)

    # Calculamos la frecuencia de los últimos 40 días del trabajador asociado a la licencia médica.
    df_licencias['frecuencia_trabajador_40D'] = count_licenses_by_entity(df_licencias, entity_col='rut_trabajador', window_days=40)

    # Calculamos la frecuencia de los últimos 20 días del trabajador asociado a la licencia médica.
    df_licencias['frecuencia_trabajador_20D'] = count_licenses_by_entity(df_licencias, entity_col='rut_trabajador', window_days=20)

    # Calculamos el reposo otorgado de los últimos 60 días del trabajador asociado a la licencia médica.
    df_licencias['reposo_trabajador_60D'] = count_dias_reposo_by_entity(df_licencias, entity_col='rut_trabajador', window_days=60)

    # Calculamos el reposo otorgado de los últimos 40 días del trabajador asociado a la licencia médica.
    df_licencias['reposo_trabajador_40D'] = count_dias_reposo_by_entity(df_licencias, entity_col='rut_trabajador', window_days=40)

    # Calculamos el reposo otorgado de los últimos 20 días del trabajador asociado a la licencia médica.
    df_licencias['reposo_trabajador_20D'] = count_dias_reposo_by_entity(df_licencias, entity_col='rut_trabajador', window_days=20)

    # Calculamos el número de médicos distintos que ha consultado un trabajador en los últimos 60 días.
    df_licencias['n_medicos_distintos_xtrabajador_60D'] = count_distinct_entities(df_licencias, 'rut_trabajador', 'rut_medico', window_days=60)

    # Calculamos el número de empleadores distintos a los que un trabajador ha emitido licencias en los últimos 60 días.
    df_licencias['n_empleadores_distintos_xtrabajador_60D'] = count_distinct_entities(df_licencias, 'rut_trabajador', 'rut_empleador', window_days=60)

    # Calculamos la desviación estándar de los días de reposo que ha recibido un trabajador en los últimos 60 días.
    df_licencias['desviacion_reposo_trabajador_60D'] = desviacion_reposo_trabajador(df_licencias, window_days=60)

    #########################################################################################################################
    # Atributos del profesional médico
    #########################################################################################################################
    # Calculamos la recencia del profesional médico asociado a la licencia médica.
    df_licencias = df_licencias.sort_values(by=['rut_medico', 'fecha_emision'])
    df_licencias['recencia_medico'] = df_licencias.groupby('rut_medico')['fecha_emision'].diff().dt.total_seconds().fillna(2628002) / 60 # 1 mes en minutos

    # Calculamos la frecuencia de los últimos 30 días del profesional médico asociado a la licencia médica.
    df_licencias['frecuencia_medico_30D'] = count_licenses_by_entity(df_licencias, entity_col='rut_medico', window_days=30)

    # Calculamos la frecuencia de los últimos 15 días del profesional médico asociado a la licencia médica.
    df_licencias['frecuencia_medico_15D'] = count_licenses_by_entity(df_licencias, entity_col='rut_medico', window_days=15)

    # Calculamos la frecuencia de los últimos 7 días del profesional médico asociado a la licencia médica.
    df_licencias['frecuencia_medico_7D'] = count_licenses_by_entity(df_licencias, entity_col='rut_medico', window_days=7)

    # Calculamos el reposo otorgado de los últimos 30 días del profesional médico asociado a la licencia médica.
    df_licencias['reposo_medico_30D'] = count_dias_reposo_by_entity(df_licencias, entity_col='rut_medico', window_days=30)

    # Calculamos el reposo otorgado de los últimos 15 días del profesional médico asociado a la licencia médica.
    df_licencias['reposo_medico_15D'] = count_dias_reposo_by_entity(df_licencias, entity_col='rut_medico', window_days=15)

    # Calculamos el reposo otorgado de los últimos 7 días del profesional médico asociado a la licencia médica.
    df_licencias['reposo_medico_7D'] = count_dias_reposo_by_entity(df_licencias, entity_col='rut_medico', window_days=7)

    # Cantidad de licencias médicas emitidas en los últimos 20, 40 y 60 minutos por parte del profesional emisor asociado a la licencia médica.
    resultados_minutos = count_licenses_numpy_minutes(df_licencias, window_minutes=[20, 40, 60])
    for key, serie in resultados_minutos.items():
        df_licencias[key] = serie

    # Calcular el máximo de licencias emitidas por día dentro de los 30 días previos del profesional médico asociado a la licencia médica.
    df_licencias['max_licencias_dia_30D'] = max_licenses_per_time_period(df_licencias, window_days=30, window_type="day")

    # Cantidad de licencias por código de diagnostico.
    df_licencias = count_licenses_by_diagnosis(df_licencias, window_days=30, cods_list=['J', 'F', 'M'], entity_col='rut_medico')

    # Calcular el máximo de días de reposo otorgados en un solo día dentro de los 30 días previos del profesional médico asociado a la licencia médica.
    df_licencias['max_rest_days_30d'] = max_rest_days_per_time_period(df_licencias, window_days=30, window_type="day")

    # Calculamos los días que tardó el médico en alcanzar el umbral de licencias médicas emitidas y cuántas licencias emitió posterior a eso, en los últimos 30 días.
    df_licencias = calcular_dias_para_umbral(df_licencias, umbral=360)

    # Calculamos el número de trabajadores distintos que ha licenciado un médico en los últimos 60 días.
    df_licencias['n_trabajadores_distintos_xmedico_60D'] = count_distinct_entities(df_licencias, 'rut_medico', 'rut_trabajador', window_days=60)

    # Calculamos el número de empleadores distintos que ha licenciado un médico en los últimos 60 días.
    df_licencias['n_empleadores_distintos_xmedico_60D'] = count_distinct_entities(df_licencias, 'rut_medico', 'rut_empleador', window_days=60)

    # Calculamos el índice de concentración HHI por médico para sus empleadores en los últimos 60 días.
    df_licencias['hhi_empleadores_por_medico_60D'] = calcular_hhi_empleadores(df_licencias, window_days=60)

    # Calculamos la cantidad de licencias de forma remota y presencial para cada médico en los últimos 30 días.
    df_licencias = count_licenses_by_otorgamiento(df_licencias, entity_col='rut_medico', window_days=30)

    #########################################################################################################################
    # Atributos del empleador
    #########################################################################################################################

    # Calculamos la recencia del trabajador asociado a la licencia médica.
    df_licencias = df_licencias.sort_values(by=['rut_empleador', 'fecha_emision'])
    df_licencias['recencia_empleador'] = df_licencias.groupby('rut_empleador')['fecha_emision'].diff().dt.total_seconds().fillna(2628002) / 60 # 1 mes en minutos

    # Calculamos la frecuencia de los últimos 60 días del empleador asociado a la licencia médica. Ahora, lo dividimos por la cantidad de trabajadores del empleador.
    df_licencias['frecuencia_empleador_60D'] = count_licenses_by_empleador(df_licencias, window_days=60) / df_licencias['n_trabajadores']

    # Calculamos la frecuencia de los últimos 40 días del empleador asociado a la licencia médica.
    df_licencias['frecuencia_empleador_40D'] = count_licenses_by_empleador(df_licencias, window_days=40) / df_licencias['n_trabajadores']

    # Calculamos la frecuencia de los últimos 20 días del empleador asociado a la licencia médica.
    df_licencias['frecuencia_empleador_20D'] = count_licenses_by_empleador(df_licencias, window_days=20) / df_licencias['n_trabajadores']

    # Calculamos el reposo otorgado de los últimos 60 días del empleador asociado a la licencia médica.
    df_licencias['reposo_empleador_60D'] = count_dias_reposo_by_empleador(df_licencias, window_days=60) / df_licencias['n_trabajadores']

    # Calculamos el reposo otorgado de los últimos 40 días del empleador asociado a la licencia médica.
    df_licencias['reposo_empleador_40D'] = count_dias_reposo_by_empleador(df_licencias, window_days=40) / df_licencias['n_trabajadores']

    # Calculamos el reposo otorgado de los últimos 20 días del empleador asociado a la licencia médica.
    df_licencias['reposo_empleador_20D'] = count_dias_reposo_by_empleador(df_licencias, window_days=20) / df_licencias['n_trabajadores']

    # Calculamos cuántos trabajadores distintos de un mismo empleador han recibido licencias los últimos 60 días.
    df_licencias['n_trabajadores_distintos_xempleador_60D'] = count_distinct_entities(df_licencias, 'rut_empleador', 'rut_trabajador', window_days=60) / df_licencias['n_trabajadores']

    # Calculamos cuántos médicos distintos han emitido licencias para trabajadores de un mismo empleador los últimos 60 días.
    df_licencias['n_medicos_distintos_xempleador_60D'] = count_distinct_entities(df_licencias, 'rut_empleador', 'rut_medico', window_days=60) / df_licencias['n_trabajadores']

    # Cantidad de licencias por código de diagnostico para cada empleador en los últimos 30 días.
    df_licencias = count_licenses_by_diagnosis(df_licencias, window_days=30, cods_list=['J', 'F', 'M'], entity_col='rut_empleador')

    #########################################################################################################################
    # Interacción entre trabajador, médico y empleador
    #########################################################################################################################

    # Número de licencias emitidas por parte del médico al profesional que se le emitió la licencia actual.
    df_licencias['historial_trabajador_medico'] = df_licencias.groupby(['rut_medico', 'rut_trabajador']).cumcount()

    # Número de licencias emitidas por parte del médico al empleador que se le emitió la licencia actual.
    df_licencias = df_licencias.sort_values(by=['rut_medico', 'rut_empleador', 'fecha_emision'])
    df_licencias['historial_empleador_medico'] = df_licencias.groupby(['rut_medico', 'rut_empleador']).cumcount()

    # Número de licencias del médico en los últimos 30 días x (el número de licencias del trabajador en los últimos 60 días)
    df_licencias['ponderado_medico_trabajador'] = df_licencias['frecuencia_medico_30D'] * (df_licencias['frecuencia_trabajador_60D'])

    #########################################################################################################################
    # Añadimos valores faltantes
    #########################################################################################################################
    # se va a gestionar los missing values de la edad del trabajador
    df_licencias.fillna({'edad_trabajador': df_licencias['edad_trabajador'].mean()}, inplace=True)

    # se va a gestionar los missing values de historial_empleador_medico
    df_licencias.fillna({'historial_empleador_medico': 0}, inplace=True)


    #########################################################################################################################
    # Filtramos el periodo de tiempo al que queremos analizar (y tiene al menos 60 días de datos). Por ejemplo: queremos calcular para Abril de 2025
    # En este caso procesamos la información de febrero, marzo y abril, lo correcto es filtrar y solo mantener las licencias de abril porque son las que tienen al menos 60 días de información.
    #########################################################################################################################}
    # df_seleccion = df_licencias[(df_licencias['fecha_emision'].dt.year == 2025) & (df_licencias['fecha_emision'].dt.month.isin([4]))].reset_index(drop=True)

    # Puedes guardar el resultado si lo deseas:
    # df_seleccion.to_csv('df_licencias_procesado.csv', index=False)
    df_licencias_exec = exec_anomalias(df_licencias)
    insert_anomalias(df_licencias_exec)
