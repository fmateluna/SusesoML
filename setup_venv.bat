@echo off

REM Ruta del archivo requirements.txt
set "requirementsPath=requirements.txt"

REM Crear el entorno virtual
python -m venv venv

REM Activar el entorno virtual
call venv\Scripts\activate

REM Instalar los módulos desde requirements.txt
pip install -r %requirementsPath%

REM Instalar uvicorn manualmente si no está en requirements.txt
pip install uvicorn

REM Verificar instalación
pip list

REM Desactivar el entorno virtual
deactivate

echo.
echo "Entorno virtual configurado y paquetes instalados correctamente."
echo "Puedes activar el entorno virtual usando 'call venv\Scripts\activate'."
pause
