import pandas as pd
import pickle
import sys
import os

# Lista de columnas necesarias para ejecutar el modelo
required_columns = [
    'especialidad_profesional',
    'cod_diagnostico_principal',
    'dias_reposo',
    'fecha_emision'
]

def validar_columnas(df, columnas_requeridas):
    faltantes = [col for col in columnas_requeridas if col not in df.columns]
    if faltantes:
        print(f"Error: faltan las siguientes columnas en los datos: {faltantes}")
        sys.exit(1)

def main():
    if len(sys.argv) < 3:
        print("Uso: python business_test.py <modelo.pkl> <datos.csv> [archivo_salida.csv]")
        sys.exit(1)

    modelo_path = sys.argv[1]
    datos_path = sys.argv[2]
    salida_path = sys.argv[3] if len(sys.argv) > 3 else "resultado.csv"

    # Cargar modelo
    if not os.path.exists(modelo_path):
        print(f"Error: el archivo del modelo '{modelo_path}' no existe.")
        sys.exit(1)

    with open(modelo_path, "rb") as f:
        model = pickle.load(f)

    # Cargar datos
    if not os.path.exists(datos_path):
        print(f"Error: el archivo de datos '{datos_path}' no existe.")
        sys.exit(1)

    df = pd.read_csv(datos_path)

    # Validar columnas necesarias
    validar_columnas(df, required_columns)

    # Aplicar modelo
    df_resultado = model.predict_prob(df)

    # Guardar resultado
    df_resultado.to_csv(salida_path, index=False)
    print(f"Procesamiento completado. Resultados guardados en {salida_path}")

if __name__ == "__main__":
    main()