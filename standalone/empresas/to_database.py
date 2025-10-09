import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

# Configuración de la conexión a PostgreSQL
db_host = "192.168.150.84"
db_port = "5432"
db_name = "suseso_ml"
db_user = "postgres"
db_pass = "IDKFA2025"
schema_table = "ml.empresa"
input_file = "./empresas_transformado.csv"
chunksize = 100000  # Procesar 100,000 filas a la vez

# Columnas esperadas en el CSV (deben coincidir con la tabla ml.empresas)
columns = [
    'anio_comercial', 'rut_empresa', 'razon_social', 'tramo_ventas', 'num_trabajadores',
    'fecha_inicio_actividades', 'fecha_termino_giro', 'fecha_primera_inscripcion',
    'tipo_termino_giro', 'tipo_contribuyente', 'subtipo_contribuyente',
    'tramo_capital_positivo', 'tramo_capital_negativo', 'rubro_economico',
    'subrubro_economico', 'actividad_economica', 'region', 'provincia', 'comuna'
]

# Conectar a la base de datos
try:
    conn = psycopg2.connect(
        host=db_host,
        port=db_port,
        dbname=db_name,
        user=db_user,
        password=db_pass
    )
    cur = conn.cursor()

    # Consulta de inserción con ON CONFLICT DO NOTHING para manejar duplicados
    insert_query = f"""
    INSERT INTO {schema_table} ({', '.join(columns)})
    VALUES %s
    ON CONFLICT (rut_empresa) DO NOTHING;
    """

    # Procesar el CSV transformado en chunks
    for chunk in pd.read_csv(input_file, delimiter=',', encoding='utf-8', chunksize=chunksize):
        # Verificar que las columnas del CSV coincidan
        if list(chunk.columns) != columns:
            raise ValueError("Las columnas del CSV no coinciden con las esperadas en la tabla.")

        # Manejar valores vacíos: reemplazar '' con None
        chunk = chunk.replace('', None)

        # Convertir columnas de fecha a formato 'YYYY-MM-DD' o None
        date_columns = ['fecha_inicio_actividades', 'fecha_termino_giro', 'fecha_primera_inscripcion']
        for col in date_columns:
            chunk[col] = pd.to_datetime(chunk[col], format='%d-%m-%Y', errors='coerce').dt.strftime('%Y-%m-%d')
            chunk[col] = chunk[col].where(chunk[col].notnull(), None)

        # Convertir el chunk a lista de tuplas para execute_values
        data = [tuple(row) for row in chunk.itertuples(index=False, name=None)]

        # Ejecutar la inserción en batch
        if data:
            execute_values(cur, insert_query, data)
            conn.commit()
            print(f"Insertadas {len(data)} filas en {schema_table}")

except Exception as e:
    print(f"Error: {str(e)}")
    conn.rollback()

finally:
    # Cerrar la conexión
    cur.close()
    conn.close()

print("Proceso completado: datos insertados en la tabla ml.empresas con manejo de duplicados.")