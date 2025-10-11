# Proyecto SUSESO ML

## Descripción General

El proyecto SUSESO ML es un sistema integral diseñado para la gestión, análisis y procesamiento de licencias médicas electrónicas (LM) en Chile. Su objetivo principal es centralizar información relevante sobre licencias (diagnósticos, prestadores, etc.) y aplicar modelos de Machine Learning y reglas de negocio para la detección de anomalías y el cálculo de scores de propensión.

La arquitectura del sistema está diseñada para ser modular, escalable y eficiente, utilizando una API RESTful para la interacción y procesamiento de datos en segundo plano.

## Características Principales

1.  **API RESTful:** Interfaz para la consulta y el procesamiento de licencias médicas, construida con FastAPI.
2.  **Procesamiento Asíncrono:** Ejecución de tareas de larga duración (cálculo de umbrales, anomalías, scores) en segundo plano para no bloquear la API, con gestión de estado y caching.
3.  **Análisis de Licencias:**
    *   **Cálculo de Umbrales:** Modelos que evalúan el comportamiento de los profesionales médicos basándose en límites de emisión de licencias.
    *   **Detección de Anomalías:** Identificación de patrones inusuales en las licencias médicas.
    *   **Scores de Propensión:** Asignación de puntuaciones basadas en reglas de negocio para predecir ciertos comportamientos.
4.  **Interacción con Base de Datos:** Conexión robusta y eficiente con bases de datos PostgreSQL/DuckDB para almacenamiento y consulta de datos.
5.  **Modularidad y Reusabilidad (Principios DRY):** El código está estructurado en módulos bien definidos, con utilidades compartidas para evitar la repetición de código y facilitar el mantenimiento.

## Tecnologías Utilizadas

*   **Python:** Lenguaje de programación principal.
*   **FastAPI:** Framework para la construcción de la API web.
*   **Pydantic:** Para la definición y validación de modelos de datos (solicitudes y respuestas de la API).
*   **Pandas & NumPy:** Para el procesamiento y análisis eficiente de datos tabulares.
*   **SQLAlchemy:** ORM para la interacción con la base de datos.
*   **PostgreSQL / DuckDB:** Bases de datos para almacenamiento y consulta.
*   **Dill:** Para la serialización y deserialización de modelos de reglas de negocio.
*   **Threading & Multiprocessing:** Para la ejecución de tareas en segundo plano.

## Estructura del Proyecto

El proyecto sigue una estructura modular para organizar el código de manera lógica:

```
.
├── api/
│   └── endpoints.py             # Define los puntos de entrada de la API.
├── core/
│   ├── anomalias.py             # Lógica para el cálculo de anomalías.
│   ├── database.py              # Configuración de la conexión a la base de datos.
│   ├── manager_anomalias.py     # (Vacío, puede ser para futuras extensiones)
│   ├── manager_score.py         # Gestión y ejecución de modelos de reglas de negocio (scores).
│   ├── manager_umbral.py        # Lógica para el procesamiento de datos de umbrales.
│   ├── manager.py               # Orquestación de procesos y formateo de respuestas.
│   ├── semaforo.py              # Lógica para el cálculo del "semáforo Watson".
│   ├── services.py              # Funciones de interacción con la base de datos.
│   └── utils/                   # Módulos de utilidad compartidos.
│       ├── __init__.py
│       ├── db_utils.py          # Decorador para la gestión de sesiones de DB.
│       ├── license_processing.py# Funciones comunes para el procesamiento de licencias.
│       └── task_manager.py      # Gestión de tareas asíncronas y caching.
├── models/
│   └── consultas.py             # Definiciones de modelos Pydantic para la API.
├── sql/
│   └── *.sql                    # Archivos SQL con las consultas a la base de datos.
├── README.md                    # Este archivo.
└── main.py                      # Punto de entrada de la aplicación FastAPI.

```

## Módulos Centrales y su Funcionamiento

### `api/endpoints.py`

*   **Propósito:** Define los endpoints de la API RESTful utilizando FastAPI. Es el punto de entrada para todas las solicitudes externas.
*   **Funcionamiento:**
    *   Recibe las solicitudes HTTP y valida los datos de entrada con modelos Pydantic (`models/consultas.py`).
    *   Utiliza el `task_manager` (`core/utils/task_manager.py`) para iniciar tareas de procesamiento de larga duración en segundo plano (ej. consultas de licencias, cálculo de semáforos) y gestionar su estado y resultados en caché.
    *   Retorna respuestas JSON o CSV.

### `core/manager.py`

*   **Propósito:** Actúa como orquestador principal para la lógica de negocio compleja.
*   **Funcionamiento:**
    *   Coordina la ejecución de diferentes procesos (cálculo de scores, umbrales, anomalías).
    *   Maneja la conversión de DataFrames de Pandas a formatos de respuesta (JSON, CSV).
    *   Contiene la lógica para `propensy_score`, `process_umbral_task`, `consulta_licencia_from_rest`, entre otros.

### `core/services.py`

*   **Propósito:** Centraliza todas las interacciones con la base de datos.
*   **Funcionamiento:**
    *   Contiene funciones para ejecutar consultas SQL (`execute_query`), actualizar registros (`update_propensity_score_licencias`, `insert_umbrales`, `insert_anomalias`, `guardar_semaforo`) y consultar datos específicos (`consulta_licencia`, `consulta_semaforo`, `query_masivo`, etc.).
    *   Todas las funciones de interacción con la DB están decoradas con `@db_session` (`core/utils/db_utils.py`) para asegurar una gestión transaccional y robusta de las sesiones.

### `core/anomalias.py`

*   **Propósito:** Implementa la lógica para el cálculo de diversas características y la detección de anomalías en las licencias médicas.
*   **Funcionamiento:**
    *   Procesa DataFrames de licencias, añadiendo columnas con métricas como recencia, frecuencia, días de reposo, número de médicos/empleadores distintos, etc.
    *   Utiliza funciones de procesamiento de licencias compartidas desde `core/utils/license_processing.py`.
    *   Integra la ejecución de modelos de anomalías (`exec_anomalias`) y la inserción de resultados en la DB (`insert_anomalias`).

### `core/manager_umbral.py`

*   **Propósito:** Contiene la lógica específica para el procesamiento de datos relacionados con los umbrales de comportamiento.
*   **Funcionamiento:**
    *   Prepara los datos de licencias para el cálculo de umbrales, aplicando filtros y calculando frecuencias por entidad.
    *   Utiliza funciones de procesamiento de licencias compartidas desde `core/utils/license_processing.py`.

### `core/manager_score.py`

*   **Propósito:** Gestiona la carga y ejecución de modelos de reglas de negocio (Business Rules) serializados.
*   **Funcionamiento:**
    *   Carga modelos `.pkl` (dill) que encapsulan reglas de negocio.
    *   Ejecuta estas reglas sobre DataFrames de licencias para calcular scores de propensión.
    *   Maneja el almacenamiento de los resultados de los scores en la base de datos.

### `core/semaforo.py`

*   **Propósito:** Implementa la lógica para el cálculo del "Semáforo Watson", un indicador que combina reglas de negocio, umbrales y anomalías para evaluar el riesgo de los médicos.
*   **Funcionamiento:**
    *   Recibe DataFrames con scores de reglas de negocio, umbrales y anomalías.
    *   Aplica lógica de agregación y cálculo para generar métricas de semáforo por médico.
    *   Guarda los resultados del semáforo en la base de datos.

## Módulos de Utilidad (`core/utils`)

Estos módulos fueron creados para centralizar funcionalidades comunes, promoviendo el principio DRY (Don't Repeat Yourself) y mejorando la mantenibilidad del código.

### `core/utils/task_manager.py`

*   **Propósito:** Proporciona una solución genérica para la gestión de tareas asíncronas y el caching de sus resultados.
*   **Funcionamiento:**
    *   `TaskManager` (instanciado globalmente como `task_manager`) permite generar hashes únicos para las solicitudes.
    *   `check_or_start_task`: Verifica si una tarea ya está en caché; si no, la inicia en un hilo separado y almacena su estado (`processing`, `finished`, `error`) y resultado.
    *   `get_task_status`: Permite consultar el estado y los resultados de una tarea en curso o completada.

### `core/utils/license_processing.py`

*   **Propósito:** Centraliza funciones comunes de procesamiento de DataFrames de licencias que eran duplicadas en `core/anomalias.py` y `core/manager_umbral.py`.
*   **Funcionamiento:**
    *   Incluye funciones como `count_licenses_by_entity`, `count_licenses_by_otorgamiento`, `count_licenses_by_diagnosis`, que calculan métricas basadas en ventanas de tiempo y agrupaciones por entidad.

### `core/utils/db_utils.py`

*   **Propósito:** Simplifica y estandariza la interacción con la base de datos mediante un decorador.
*   **Funcionamiento:**
    *   El decorador `@db_session` encapsula la lógica de apertura, commit, rollback y cierre de sesiones de SQLAlchemy.
    *   Permite que las funciones de `core/services.py` se enfoquen únicamente en la lógica SQL, sin preocuparse por la gestión explícita de la sesión.

## Conceptos Clave

### Principio DRY (Don't Repeat Yourself)

La refactorización reciente se centró en aplicar el principio DRY. Esto se logró identificando y centralizando bloques de código repetidos (como las funciones de procesamiento de licencias y la gestión de sesiones de base de datos) en módulos de utilidad dedicados (`core/utils`). Esto reduce la redundancia, facilita el mantenimiento y mejora la consistencia del código.

### Procesamiento Asíncrono y Caching

Para manejar operaciones que pueden tomar tiempo (ej. consultas complejas a la DB, cálculos intensivos), el sistema utiliza un patrón asíncrono. Las solicitudes de la API inician estas tareas en hilos separados a través del `task_manager`. Los resultados se almacenan en un caché, permitiendo que la API responda rápidamente con el estado de la tarea y que los clientes consulten los resultados una vez que estén disponibles.

### Gestión de Sesiones de Base de Datos

El decorador `@db_session` en `core/utils/db_utils.py` abstrae la complejidad de la gestión de sesiones de SQLAlchemy. Cada función decorada recibe automáticamente una sesión de base de datos, y el decorador se encarga de realizar el `commit` si la función se ejecuta sin errores, el `rollback` en caso de excepción, y el cierre de la sesión en cualquier caso. Esto garantiza la integridad de los datos y la liberación de recursos.

### Optimización de Consultas SQL

Se han implementado mejoras en el rendimiento de las consultas SQL para asegurar una mayor eficiencia en la interacción con la base de datos. Las optimizaciones clave incluyen:

1.  **`sql/consulta_licencias_periodo.sql`**:
    *   **Mejora**: La cláusula `WHERE` que filtra por año y mes ha sido modificada para utilizar comparaciones directas de rangos de fechas en lugar de funciones `TO_CHAR`.
    *   **Beneficio**: Esto permite que la base de datos aproveche los índices existentes en la columna `fecha_emision`, acelerando significativamente la búsqueda de licencias por período al evitar escaneos completos de la tabla.

2.  **`sql/consulta1.sql`**:
    *   **Mejora**: La condición de búsqueda para `especialidad_profesional` ha sido cambiada de la función `similarity` a `ILIKE`.
    *   **Beneficio**: La función `similarity` es computacionalmente costosa sin configuraciones de índices avanzadas. `ILIKE` ofrece una forma más eficiente de realizar búsquedas de texto parcial e insensible a mayúsculas/minúsculas, mejorando el rendimiento de la consulta. Para una eficiencia óptima con `ILIKE` en búsquedas de texto libre, se recomienda la instalación de la extensión `pg_trgm` y la creación de índices `GIN` o `GIST` en la columna `descripcion_especialidad_profesional`.

## Modelos de Umbrales

Estos modelos calculan un score por licencia médica que se basa en umbrales que describen límites de comportamientos normales de los médicos que emiten dicha licencia. Para esto, estos modelos de umbrales reciben todas las licencias emitidas por el profesional médico durante los 30 días previos a su emisión.

*   `modelo_umbrales_30`: `window_days=30`
*   `modelo_umbrales_15`: `window_days=15`
*   `modelo_umbrales_7`: `window_days=7`

## Metodología de Procesamiento Asíncrono (Ej. Cálculo de Umbrales)

El flujo para el procesamiento de tareas de larga duración, como el cálculo de umbrales, sigue el siguiente patrón:

1.  **Solicitud Inicial (Endpoint API):** Un endpoint de la API recibe una solicitud (ej. `POST /umbral/create`).
2.  **Generación de Hash y Verificación de Caché:** Se genera un hash único para la solicitud. El `task_manager` verifica si ya existe una tarea en curso o completada para este hash.
3.  **Inicio de Tarea Asíncrona:** Si la tarea no está en caché, el `task_manager` la inicia en un hilo o proceso separado.
4.  **Registro de Estado:** El estado de la tarea se registra en la base de datos (`ml.umbral_data`) y/o en el caché del `task_manager` (ej. `init`, `extract_data`, `process_data`, `calc_data_anomaly`, `finish`, `error`).
5.  **Respuesta Inmediata (API):** La API responde inmediatamente con el estado actual de la tarea (ej. "processing").
6.  **Procesamiento en Segundo Plano:** La tarea asíncrona realiza sus operaciones (ej. extracción de datos, procesamiento, cálculo de anomalías) y actualiza su estado en la base de datos y/o caché.
7.  **Consulta de Estado/Resultados (Endpoint API):** Un endpoint separado (ej. `GET /umbral/status/{request_hash}`) permite a los clientes consultar el estado y, una vez completada, los resultados de la tarea.

## Tablas Involucradas

*   `ml.umbral_data`: Almacena el estado de las solicitudes de cálculo de umbrales (hash, fecha, días, entidad, estado, created_at).
*   `ml.umbrales`: Contiene los resultados detallados de los cálculos de umbrales por licencia.
*   `ml.anomalias`: Almacena los resultados de la detección de anomalías por licencia.
*   `ml.propensity_score`: Guarda los scores de propensión calculados por las reglas de negocio.
*   `ml.semaforo_resultados`: Almacena los resultados agregados del "Semáforo Watson" por médico.

## Instalación y Ejecución

### Requisitos

*   Python 3.8+
*   Poetry (recomendado para gestión de dependencias) o pip
*   Acceso a una base de datos PostgreSQL o DuckDB.

### Configuración del Entorno

1.  **Clonar el repositorio:**
    ```bash
    git clone <URL_DEL_REPOSITORIO>
    cd SusesoML
    ```
2.  **Crear y activar el entorno virtual (con Poetry):**
    ```bash
    poetry install
    poetry shell
    ```
    O con pip:
    ```bash
    python -m venv .venv
    ./.venv/Scripts/activate  # En Windows
    # source .venv/bin/activate # En Linux/macOS
    pip install -r requirements.txt
    ```
3.  **Configurar variables de entorno:**
    Crea un archivo `.env` en la raíz del proyecto con las credenciales de tu base de datos:
    ```
    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=suseso_db
    DB_USER=user
    DB_PASS=password
    ```
4.  **Configurar extensiones de PostgreSQL (si aplica):**
    Asegúrate de que las siguientes extensiones estén activadas en tu base de datos:
    ```sql
    CREATE EXTENSION IF NOT EXISTS unaccent;
    CREATE EXTENSION IF NOT EXISTS pg_trgm;
    ```

### Ejecución de la Aplicación

Para iniciar el servidor FastAPI:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

La API estará disponible en `http://0.0.0.0:8000/lm/ml`. Puedes acceder a la documentación interactiva en `http://0.0.0.0:8000/lm/ml/docs`.