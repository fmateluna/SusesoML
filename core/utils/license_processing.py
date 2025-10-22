import pandas as pd
import numpy as np

def count_licenses_by_entity(df, entity_col='rut_medico', window_days=30):
    """
    Cuenta el número de licencias emitidas por una entidad (por ejemplo, un médico) en una ventana de tiempo previa
    a la fecha de emisión de cada licencia. Optimizada usando NumPy para eficiencia.

    Parámetros:
        df (pd.DataFrame): DataFrame que debe contener las columnas 'fecha_emision' y la columna de entidad (por defecto 'rut_medico').
        entity_col (str): Columna que identifica la entidad a agrupar (por ejemplo, 'rut_medico').
        window_days (int): Ventana de tiempo hacia atrás en días para el conteo.

    Retorna:
        pd.Series: Serie con el mismo índice que el DataFrame original, donde cada valor indica la cantidad de licencias
        emitidas por la entidad correspondiente en los window_days previos a la fecha de emisión de cada licencia.
    """
    df_sorted = df.sort_values(by=[entity_col, 'fecha_emision'])
    fecha = df_sorted['fecha_emision'].values
    entity = df_sorted[entity_col].values
    index = df_sorted.index.values

    result = np.zeros(len(df_sorted), dtype=int)
    pos = 0

    while pos < len(df_sorted):
        # Encuentra el bloque actual
        curr_entity = entity[pos]
        start = pos
        while pos < len(df_sorted) and entity[pos] == curr_entity:
            pos += 1
        end = pos

        fechas_entidad = fecha[start:end]
        dias = (fechas_entidad - fechas_entidad[0]) / np.timedelta64(1, 'D')
        dias = dias.astype(np.int32)

        # Busca inicio de la ventana para cada elemento usando searchsorted
        left_idxs = np.searchsorted(dias, dias - window_days, side='left')
        counts = np.arange(len(dias)) - left_idxs

        result[start:end] = counts

    return pd.Series(result, index=df_sorted.index).reindex(df.index)

def count_licenses_by_otorgamiento(df, entity_col='rut_medico', window_days=30):
    """
    Cuenta licencias remotas y presenciales emitidas por una entidad (como un médico) en una ventana de tiempo
    previa a cada licencia.

    Se asegura de mantener el índice original del DataFrame para una asignación directa y segura del resultado.

    Parámetros:
        df (pd.DataFrame): DataFrame que debe contener 'fecha_emision', 'marca_otorgamiento' y la columna de entidad.
        entity_col (str): Columna que identifica la entidad a agrupar (por ejemplo, 'rut_medico').
        window_days (int): Ventana de tiempo hacia atrás en días.

    Retorna:
        pd.DataFrame: El mismo DataFrame de entrada con dos columnas nuevas:
            - n_remotas_{window_days}D
            - n_presenciales_{window_days}D
    """
    df = df.copy()
    df['fecha_emision'] = pd.to_datetime(df['fecha_emision'])
    df['marca_otorgamiento'] = df['marca_otorgamiento'].fillna('NO_REMOTA')

    # Guardar índice original
    original_index = df.index

    # Ordenar para el cálculo
    df_sorted = df.sort_values(by=[entity_col, 'fecha_emision'])
    df_sorted['dias'] = (df_sorted['fecha_emision'] - df_sorted['fecha_emision'].min()).dt.days

    # Series para almacenar los resultados manteniendo el índice original
    n_remotas = pd.Series(0, index=df_sorted.index, dtype=int)
    n_presenciales = pd.Series(0, index=df_sorted.index, dtype=int)

    for entity_value, group in df_sorted.groupby(entity_col):
        dias = group['dias'].values
        otorgamientos = group['marca_otorgamiento'].values

        for i in range(len(group)):
            start_date = dias[i] - window_days
            mask = (dias >= start_date) & (dias < dias[i])
            idx = group.index[i]

            n_remotas.loc[idx] = np.sum(otorgamientos[mask] == 'REMOTA')
            n_presenciales.loc[idx] = np.sum(otorgamientos[mask] != 'REMOTA')

    # Reindexar al DataFrame original
    df[f'n_remotas_{window_days}D'] = n_remotas.reindex(original_index)
    df[f'n_presenciales_{window_days}D'] = n_presenciales.reindex(original_index)

    return df

def count_licenses_by_diagnosis(df, window_days=30, cods_list=None, entity_col='rut_medico'):
    """
    Cuenta licencias por diagnóstico (letra inicial del código) en una ventana hacia atrás, agrupando por entidad (médico o empleador),
    asegurando que los resultados estén alineados con el índice original del DataFrame.

    Parámetros:
        df (pd.DataFrame): Debe tener columnas 'fecha_emision', 'cod_diagnostico_principal' y la entidad ('rut_medico' o 'rut_empleador').
        window_days (int): Tamaño de la ventana temporal hacia atrás.
        cods_list (list): Lista de letras de diagnóstico a incluir. Si es None, se usan todas.
        entity_col (str): Columna por la cual agrupar (por defecto 'rut_medico', pero puede ser 'rut_empleador').

    Retorna:
        pd.DataFrame: Con columnas adicionales de frecuencia para cada letra de diagnóstico, nombradas con la entidad.
    """
    df = df.copy()
    df['diagn_letter'] = df['cod_diagnostico_principal'].str[0]
    df['fecha_emision'] = pd.to_datetime(df['fecha_emision'])
    original_index = df.index

    if cods_list is None:
        cods_list = df['diagn_letter'].dropna().unique()

    entidad_nombre = entity_col.split('_')[-1]  # Ejemplo: 'rut_medico' -> 'medico'

    # Inicializar Series para cada letra, con índice original
    results = {
        f'frecuencia_{letra}_{window_days}D_{entidad_nombre}': pd.Series(0, index=original_index)
        for letra in cods_list
    }

    for entidad, grupo in df.groupby(entity_col):
        grupo = grupo.sort_values('fecha_emision')
        fechas = grupo['fecha_emision'].values
        letras = grupo['diagn_letter'].values
        idxs = grupo.index

        for letra in cods_list:
            mask = letras == letra
            fechas_cod = fechas[mask]

            if len(fechas_cod) == 0:
                continue

            result = (
                np.searchsorted(fechas_cod, fechas, side='left') -
                np.searchsorted(fechas_cod, fechas - np.timedelta64(window_days, 'D'), side='right')
            )

            col_name = f'frecuencia_{letra}_{window_days}D_{entidad_nombre}'
            results[col_name].loc[idxs] = result

    # Agregar resultados al DataFrame original
    for col_name, serie in results.items():
        df[col_name] = serie.reindex(df.index)

    df.drop(columns=['diagn_letter'], inplace=True)
    return df
