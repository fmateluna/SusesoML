 
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



