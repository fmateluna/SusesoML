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
    df = df[[entity_col, 'fecha_emision']].copy()
    df['fecha_emision'] = pd.to_datetime(df['fecha_emision'])
    df = df.sort_values([entity_col, 'fecha_emision']).reset_index()

    entity = df[entity_col].values
    fecha = df['fecha_emision'].values.astype('datetime64[D]').astype(np.int64)
    orig_idx = df['index'].values

    changes = np.concatenate([[True], entity[1:] != entity[:-1]])
    starts = np.where(changes)[0]
    ends = np.concatenate([starts[1:], [len(df)]])

    result = np.zeros(len(df), dtype=np.int32)

    for s, e in zip(starts, ends):
        block = fecha[s:e]
        rel_days = block - block[0]
        left = np.searchsorted(rel_days, rel_days - window_days, side='left')
        result[s:e] = np.arange(e - s) - left

    return pd.Series(result, index=orig_idx).reindex(df.index)


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
    is_remota = df['marca_otorgamiento'].fillna('NO_REMOTA') == 'REMOTA'
    orig_idx = df.index

    df = df.sort_values([entity_col, 'fecha_emision']).reset_index(drop=True)
    entity = df[entity_col].values
    fecha = df['fecha_emision'].values.astype('datetime64[D]').astype(np.int64)

    changes = np.concatenate([[True], entity[1:] != entity[:-1]])
    starts = np.where(changes)[0]
    ends = np.concatenate([starts[1:], [len(df)]])

    n_remotas = np.zeros(len(df), dtype=np.int32)
    n_presenciales = np.zeros(len(df), dtype=np.int32)

    for s, e in zip(starts, ends):
        block_dates = fecha[s:e]
        block_remota = is_remota.iloc[s:e].values

        rel_days = block_dates - block_dates[0]
        window_limit = rel_days - window_days

        left_all = np.searchsorted(block_dates, block_dates - np.timedelta64(window_days, 'D'), side='left')

        cum_remota = np.cumsum(block_remota)
        cum_total = np.arange(1, e-s+1)

        prev_remota = np.where(window_limit >= 0,
                               cum_remota[np.searchsorted(rel_days, window_limit, side='left') - 1],
                               0)
        prev_remota = np.maximum(0, prev_remota)

        n_remotas[s:e] = cum_remota - prev_remota
        n_presenciales[s:e] = (cum_total - left_all) - n_remotas[s:e]

    df = df.set_index(orig_idx)
    df[f'n_remotas_{window_days}D'] = n_remotas
    df[f'n_presenciales_{window_days}D'] = n_presenciales
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
    df['fecha_emision'] = pd.to_datetime(df['fecha_emision'])
    df['diagn_letter'] = df['cod_diagnostico_principal'].astype(str).str[0].fillna('')

    if cods_list is None:
        cods_list = sorted([c for c in df['diagn_letter'].unique() if c.isalpha()])

    orig_idx = df.index
    entidad_nombre = entity_col.split('_')[-1]

    for letra in cods_list:
        df[f'frecuencia_{letra}_{window_days}D_{entidad_nombre}'] = 0

    df = df.sort_values([entity_col, 'fecha_emision'])

    entity = df[entity_col].values
    fecha = df['fecha_emision'].values.astype('datetime64[D]')
    letras = df['diagn_letter'].values

    changes = np.concatenate([[True], entity[1:] != entity[:-1]])
    starts = np.where(changes)[0]
    ends = np.concatenate([starts[1:], [len(df)]])

    col_map = {letra: f'frecuencia_{letra}_{window_days}D_{entidad_nombre}' for letra in cods_list}
    result_arrays = {letra: df[col_map[letra]].values for letra in cods_list}

    for s, e in zip(starts, ends):
        block_fechas = fecha[s:e]
        block_letras = letras[s:e]

        for letra in cods_list:
            mask = block_letras == letra
            if not mask.any():
                continue
            fechas_cod = block_fechas[mask]
            counts = np.searchsorted(fechas_cod, block_fechas, side='left') - \
                     np.searchsorted(fechas_cod, block_fechas - np.timedelta64(window_days, 'D'), side='right')
            result_arrays[letra][s:e] = counts

    for letra, arr in result_arrays.items():
        df[col_map[letra]] = arr

    df = df.drop(columns=['diagn_letter']).loc[orig_idx]
    return df