import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import spacy
from datetime import timedelta
import warnings
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
import re
import logging
reclamos_logger = logging.getLogger('reclamos_logger')

class ProcesadorReclamos:
    def __init__(self):
        self.nlp = spacy.load("es_core_news_sm")
        
    def obtenerDenuncias(self, ruta_denuncias):
        """
        Obtiene y procesa el archivo de denuncias
        
        Parámetros:
        ruta_denuncias (str): Ruta al archivo CSV de denuncias
        
        Retorna:
        pd.DataFrame: DataFrame con las denuncias procesadas
        """
        denuncias = pd.read_csv(ruta_denuncias, sep="|")
        reclamos_logger.info("Archivo cargado: PRODUCCIÓN UCLM (denuncias PAE)")
        
        # Procesamiento básico
        denuncias["sancionado"] = denuncias["tipo_sancion"].notna().astype(int)
        denuncias = denuncias[denuncias["causal_homologada"]=="Denuncia a profesional emisor"]
        denuncias.loc[:, 'fecha_ingreso'] = pd.to_datetime(denuncias['fecha_ingreso'], errors='coerce')
        
        return denuncias
    
    def obtenerRelatos(self, ruta_relatos):
        """
        Obtiene el archivo de relatos
        
        Parámetros:
        ruta_relatos (str): Ruta al archivo CSV de relatos
        
        Retorna:
        pd.DataFrame: DataFrame con los relatos
        """
        relatos = pd.read_csv(ruta_relatos, encoding='latin-1', 
                            on_bad_lines='skip', sep=",")
        reclamos_logger.info("Archivo cargado: RELATOS UCLM")
        return relatos
    
    def obtenerDetalleUCLM(self, ruta_detalle):
        """
        Obtiene el archivo de detalle UCLM
        
        Parámetros:
        ruta_detalle (str): Ruta al archivo CSV de detalle UCLM
        
        Retorna:
        pd.DataFrame: DataFrame con el detalle UCLM
        """
        detalleUCLM = pd.read_csv(ruta_detalle, encoding='latin-1', 
                                on_bad_lines='skip', sep="|")
        reclamos_logger.info("Archivo cargado: SÁBANA UCLM DETALLE (denuncias + licencias asociadas)")
        return detalleUCLM
    
    def obtenerLME(self, ruta_lme):
        """
        Obtiene y procesa el archivo LME
        
        Parámetros:
        ruta_lme (str): Ruta al archivo CSV de LME
        
        Retorna:
        pd.DataFrame: DataFrame con LME procesado
        """
        lme = pd.read_csv(ruta_lme)
        
        # Procesamiento
        lme = lme[lme['dias_reposo'] <= 365]
        lme = lme[~lme['cod_diagnostico_principal'].isin(['U07.1', 'U07.2'])]
        lme['fecha_emision'] = pd.to_datetime(lme['fecha_emision'], errors='coerce')
        lme['fecha_recepcion_empleador'] = pd.to_datetime(lme['fecha_recepcion_empleador'], errors='coerce')
        
        return lme
    
    def obtenerDatosSemaforo(self, ruta_semaforo):
        """
        Obtiene el archivo base para el semáforo
        
        Parámetros:
        ruta_semaforo (str): Ruta al archivo CSV con datos para semáforo
        
        Retorna:
        pd.DataFrame: DataFrame con datos procesados para semáforo
        """
        df = pd.read_csv(ruta_semaforo)
        reclamos_logger.info("Archivo cargado: LME con puntajes calculados RN, UM, AN")
        
        # Procesamiento
        df["propensity_score_rn"] = df["propensity_score_rn"].fillna(0).astype(int)
        df["propensity_score_umbrales"] = df["propensity_score_umbrales"].fillna(0).astype(int)
        df["propensity_score_iforest"] = df["propensity_score_iforest"].fillna(0).astype(int)
        
        return df

    def procesarRelatos(self, relatos, denuncias_filtradas):
        """
        Procesa y analiza los relatos de denuncias
        
        Parámetros:
        relatos (pd.DataFrame): DataFrame de relatos
        denuncias_filtradas (pd.DataFrame): Denuncias filtradas por fecha
        
        Retorna:
        pd.DataFrame: Denuncias con análisis de relatos
        """
        denuncias_previas_relato = pd.merge(relatos, denuncias_filtradas, 
                                          how='inner', left_on="FUN_FOLIO", 
                                          right_on="folio_fui")
        
        denuncias_previas_relato = self.count_mentions(denuncias_previas_relato, "FUN_RELATO")
        denuncias_previas_relato.drop(columns=['num_personas', "num_personas_NER", 
                                             "num_doctores", "personas_sobre_umbral", 
                                             "doctores_sobre_umbral"], inplace=True)
        
        return denuncias_previas_relato

    def count_mentions(self, df, text_column, person_thresh=2, doctor_thresh=2):
        """
        Cuenta menciones de personas y doctores en textos
        """
        people_counts = []
        people_ner_counts = []
        doctor_counts = []

        for text in df[text_column]:
            doc = self.nlp(str(text))
            people_ner = [ent.text for ent in doc.ents if ent.label_ == "PER"]
            doctors = [token.text.lower() for token in doc if token.text.lower() in ["doctor", "doctora", "dr.", "dra."]]

            people_counts.append(len(people_ner))
            people_ner_counts.append(len(set(people_ner)))
            doctor_counts.append(len(doctors))

        df["num_personas"] = people_counts
        df["num_personas_NER"] = people_ner_counts
        df["num_doctores"] = doctor_counts
        df["personas_sobre_umbral"] = (df["num_personas"] >= person_thresh).astype(int)
        df["doctores_sobre_umbral"] = (df["num_doctores"] >= doctor_thresh).astype(int)

        return df

    def procesarAdmisibilidad(self, denuncias_previas_relato, denuncias_filtradas, relatos, detalleUCLM, lme):
        """
        Procesa la admisibilidad de las denuncias
        """
        # Código de procesamiento de admisibilidad (similar al original)
        # ... (mantener la lógica existente)
        
        return denuncias_previas_relato

    def semaforoWatson(self, dataframe, mes=None, anio=None, show_results=None, 
                      sort_values_by="um", umbral_decorte=0.5, rn_ln_mes=400, 
                      umbral_deanomalias=0.5):
        """
        Calcula indicadores de alertas ('semáforos') por médico
        """
        # Implementación existente de semaforoWatson
        # ... (mantener la función original)
        
        return semaforo_watson

    def resumenMensualMedicos(self, dataframe_a_utilizar, meses, anio=None, sort_priority=None):
        """
        Genera resumen comparativo de indicadores por médico
        """
        # Implementación existente
        # ... (mantener la función original)
        
        return df_resumen

    def unir_denuncias_con_semaforo(self, df_denuncias, df_semaforo, 
                                  columnas_basicas=["folio_fui", "rut_medico", "fecha_ingreso", "sancionado", "no_admisible"]):
        """
        Une denuncias con datos del semáforo
        """
        # Implementación existente
        # ... (mantener la función original)
        
        return df

    def export_to_csv_excel_friendly(self, df, filename):
        """
        Exporta DataFrame a CSV compatible con Excel
        """
        df_copy = df.copy()
        for col in df_copy.select_dtypes(include='number').columns:
            df_copy[col] = df_copy[col].map(lambda x: f"{x:.4f}".replace('.', ','))

        df_copy.to_csv(filename, index=False, sep=';', encoding='latin-1')

    def procesarReclamos(self, mes_a_revisar_no, filter_year, config):
        """
        Método principal que inicia todo el procesamiento
        
        Parámetros:
        mes_a_revisar_no (int): Mes a revisar (1-12)
        filter_year (int): Año a revisar
        config (dict): Diccionario con rutas y configuraciones
        """
        reclamos_logger.info(f"Iniciando procesamiento para {mes_a_revisar_no}/{filter_year}")
        
        # 1. Obtener datos
        denuncias = self.obtenerDenuncias(config['ruta_denuncias'])
        relatos = self.obtenerRelatos(config['ruta_relatos'])
        detalleUCLM = self.obtenerDetalleUCLM(config['ruta_detalle_uclm'])
        lme = self.obtenerLME(config['ruta_lme'])
        df_semaforo = self.obtenerDatosSemaforo(config['ruta_semaforo'])
        
        # 2. Filtrar denuncias por fecha
        start_date = pd.to_datetime(f'{filter_year}-{mes_a_revisar_no:02d}-01')
        end_date = start_date + pd.DateOffset(months=1)
        
        denuncias_filtradas = denuncias[(denuncias['fecha_ingreso'] >= start_date) & 
                                      (denuncias['fecha_ingreso'] < end_date)]
        
        reclamos_logger.info(f"Denuncias filtradas para {start_date.strftime('%B %Y')}: {len(denuncias_filtradas)}")
        
        # 3. Procesar relatos
        denuncias_previas_relato = self.procesarRelatos(relatos, denuncias_filtradas)
        
        # 4. Procesar admisibilidad
        denuncias_previas_relato = self.procesarAdmisibilidad(
            denuncias_previas_relato, denuncias_filtradas, relatos, detalleUCLM, lme
        )
        
        # 5. Calcular semáforos
        smf = self.resumenMensualMedicos(
            df_semaforo, 
            meses=config.get('meses_semaforo', [4, 5, 6]),
            anio=filter_year
        )
        
        # 6. Unir denuncias con semáforo
        denuncias_semaforo = self.unir_denuncias_con_semaforo(denuncias_previas_relato, smf)
        
        # 7. Aplicar criterios de ordenamiento y decisión
        if config.get('ordenar_por') == "Priorización":
            denuncias_semaforo.sort_values(by="ptje_prio", ascending=False, inplace=True)
        elif config.get('ordenar_por') == "Fecha":
            denuncias_semaforo.sort_values(by="fecha_ingreso", ascending=True, inplace=True)
        
        denuncias_semaforo['decision'] = np.where(
            denuncias_semaforo['ptje_prio'] > config.get('umbral_priorizacion', 0.94), 
            'Priorizar', 
            'sin decision'
        )
        denuncias_semaforo['no_admisible'] = denuncias_semaforo['no_admisible'].replace(
            {1: 'No admisible', 0: 'sin decision'}
        )
        denuncias_semaforo['sancionado'] = denuncias_semaforo['sancionado'].replace(
            {1: 'Si', 0: 'No'}
        )
        
        # 8. Exportar resultados
        self.export_to_csv_excel_friendly(
            denuncias_semaforo, 
            config.get('nombre_archivo_salida', f"smf_denuncias_{mes_a_revisar_no}_{filter_year}.csv")
        )
        
        reclamos_logger.info("Procesamiento completado exitosamente!")
        return denuncias_semaforo

# Ejemplo de uso
def main():
    # Configuración
    config = {
        'ruta_denuncias': "./standalone/reclamos/PRODUCCIÓN UCLM_072025_v2___.csv",
        'ruta_relatos': "./standalone/reclamos/relato_uclm_24072025.csv",
        'ruta_detalle_uclm': "./standalone/reclamos/SabanaUCLMDetalle_40214_2025-7-22_5-20-2.csv",
        'ruta_lme': './standalone/reclamos/lme_capacitacion.csv',
        'ruta_semaforo': './standalone/reclamos/df_to_semaforo-julio.csv',
        'meses_semaforo': [4, 5, 6],
        'ordenar_por': "Fecha",
        'umbral_priorizacion': 0.94,
        'nombre_archivo_salida': "smf_denuncias_jun_25.csv"
    }
    
    # Parámetros principales
    mes_a_revisar_no = 6
    filter_year = 2025
    
    # Ejecutar procesamiento
    procesador = ProcesadorReclamos()
    resultado = procesador.procesarReclamos(mes_a_revisar_no, filter_year, config)
    
    return resultado

# Ejecutar si es el script principal
if __name__ == "__main__":
    resultado = main()