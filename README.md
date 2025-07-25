 
uvicorn main:app --reload    
# Proyecto SUSESO ML

## Descripción

SUSESO es un sistema diseñado para gestionar y analizar licencias médicas electrónicas (LM) en Chile. Este proyecto centraliza información sobre licencias emitidas, diagnósticos, prestadores, y otros datos relevantes, permitiendo consultas rápidas y precisas a través de una API desarrollada en Python.

## Características principales

1. **Consulta de licencias por médico**: Filtrado de licencias emitidas por un profesional específico mediante su RUT.
2. **Análisis por diagnóstico y región**: Capacidad de segmentar y analizar datos con base en diagnósticos o ubicación.
3. **Detalles de licencias**: Provisión de información detallada sobre licencias individuales, como fecha de emisión, diagnóstico, y puntajes de probabilidad.
4. **Estructura modular**: Construcción basada en principios claros de diseño, con uso de Pydantic para validación de datos y una conexión fluida a bases de datos SQL.

## Tecnologías utilizadas

- **Python**: Lenguaje principal del proyecto.
- **Pydantic**: Para la definición y validación de modelos de datos.
- **SQL**: Consultas a través de scripts personalizados.
- **Bases de datos**: PostgreSQL o DuckDB para almacenamiento y consulta.

Importante activar
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;


Modelos de umbrales: Estos modelos calculan un score por licencia medica que se basa en umbrales que describen límites de comportamientos normales de los médicos que emiten dicha licencia. Para esto, estos modelos de umbrales reciben todas las licencias emitidas por el profesional médico durante los 30 días previo a su emisión.

modelo_umbrales_30: 
window_days=30
modelo_umbrales_15
window_days=15
modelo_umbrales_7
window_days=7

Uso modelo de umbrales

import pandas as pd
import pickle
import sys

# Verifica que se pasen los argumentos correctos
if len(sys.argv) != 4:
print("Uso: python umbral_test.py <modelo.pkl> <datos.csv> <salida.csv>")
sys.exit(1)

modelo_path = sys.argv[1]
datos_path = sys.argv[2]
salida_path = sys.argv[3]

# Cargar modelo
with open(modelo_path, "rb") as f:
modelo = pickle.load(f)

# Cargar datos
df = pd.read_csv(datos_path, parse_dates=['fecha_emision']) 

# Aplicar modelo
df_resultado = modelo.predict_prob(df)

# Guardar resultado
df_resultado.to_csv(salida_path, index=False)
print(f"Resultado guardado en {salida_path}")
