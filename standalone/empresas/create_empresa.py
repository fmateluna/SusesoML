import pandas as pd

# Configuración
input_file = './empresas.csv'
output_file = './empresas_transformado.csv'
chunksize = 100000  # Procesar 100,000 filas a la vez
encoding = 'ISO-8859-1'  # Cambia esto según la codificación detectada (p.ej., 'Windows-1252')

# Lista para controlar si se escribe la cabecera
first_chunk = True

# Procesar el CSV en chunks
for chunk in pd.read_csv(input_file, delimiter=';', encoding=encoding, chunksize=chunksize):
    # Combinar RUT y DV en rut_empresa
    chunk['rut_empresa'] = chunk['RUT'].astype(str) + '-' + chunk['DV'].astype(str)

    # Renombrar columnas para que coincidan con la tabla EMPRESA
    chunk = chunk.rename(columns={
        'Año comercial': 'anio_comercial',
        'Razón social': 'razon_social',
        'Tramo según ventas': 'tramo_ventas',
        'Número de trabajadores dependie': 'num_trabajadores',
        'Fecha inicio de actividades vige': 'fecha_inicio_actividades',
        'Fecha término de giro': 'fecha_termino_giro',
        'Fecha primera inscripción de ac': 'fecha_primera_inscripcion',
        'Tipo término de giro': 'tipo_termino_giro',
        'Tipo de contribuyente': 'tipo_contribuyente',
        'Subtipo de contribuyente': 'subtipo_contribuyente',
        'Tramo capital propio positivo': 'tramo_capital_positivo',
        'Tramo capital propio negativo': 'tramo_capital_negativo',
        'Rubro económico': 'rubro_economico',
        'Subrubro económico': 'subrubro_economico',
        'Actividad económica': 'actividad_economica',
        'Región': 'region',
        'Provincia': 'provincia',
        'Comuna': 'comuna'
    })

    # Eliminar columnas originales RUT y DV
    chunk = chunk.drop(columns=['RUT', 'DV'])

    # Reordenar columnas para que coincidan con la tabla
    columns_order = [
        'anio_comercial', 'rut_empresa', 'razon_social', 'tramo_ventas', 'num_trabajadores',
        'fecha_inicio_actividades', 'fecha_termino_giro', 'fecha_primera_inscripcion',
        'tipo_termino_giro', 'tipo_contribuyente', 'subtipo_contribuyente',
        'tramo_capital_positivo', 'tramo_capital_negativo', 'rubro_economico',
        'subrubro_economico', 'actividad_economica', 'region', 'provincia', 'comuna'
    ]
    chunk = chunk[columns_order]

    # Guardar el chunk en el archivo de salida
    chunk.to_csv(output_file, sep=',', mode='a', index=False, header=first_chunk, encoding='utf-8')
    first_chunk = False  # Solo escribir la cabecera en el primer chunk

print(f"Archivo transformado guardado en: {output_file}")