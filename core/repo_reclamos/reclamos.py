from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import yaml

from core.repo_reclamos.admisibilidad import AdmisibilidadConfig, AdmisibilidadProcessor, NLPConfig
from core.repo_reclamos.priorizacion import PrioritizationConfig, PriorizacionProcessor, SemaforoConfig
from models.consultas import ReclamosRequest


reclamos_logger = logging.getLogger('reclamos_logger')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("watson-pipeline")


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# Se agrega rut_medico como parametro opcional
def build_admisibilidad_cfg(cfg: Dict[str, Any], anio : int, mes: int, rut_medico: Optional[str] = None) -> AdmisibilidadConfig:
    # Estos ya no se usan
    path_anio = str(anio)
    path_mes = f"{mes:02d}" 

    paths = cfg.get("paths", {})
    encoding = cfg.get("encoding", {})
    csv_sep = cfg.get("csv_sep", {})
    # hasta aca

    filters = cfg.get("filters", {})
    nlp_cfg = cfg.get("nlp", {})

    base_path = os.path.dirname(os.path.abspath(__file__)) + '/' 


    # Migracion de csv/xlsx a Base de datos : Se comenta la construccion de path_denuncias_pae ya que ahora se carga desde la base de datos
    # path_denuncias_pae = f"{base_path}/{paths['denuncias_pae'].replace('YYYY', path_anio).replace('MM', path_mes)}"




    return AdmisibilidadConfig(
        # Migracion de csv/xlsx a Base de datos : Se elimina path_denuncias_pae del constructor
        # path_denuncias_pae,
        # Migracion de csv/xlsx a Base de datos : enc_detalle_uclm ya no es necesario
        # enc_detalle_uclm=encoding.get("detalle_uclm"),
        # Migracion de csv/xlsx a Base de datos : Se elimina sep_denuncias_pae del constructor
        # sep_denuncias_pae=csv_sep.get("denuncias_pae", "|"),
        # Migracion de csv/xlsx a Base de datos : sep_detalle_uclm ya no es necesario
        # sep_detalle_uclm=csv_sep.get("detalle_uclm", "|"),
        causal_homologada=filters.get("causal_homologada", "Denuncia a profesional emisor"),
        mes_a_revisar=mes,
        anio=anio,
        # Se agrega el rut_medico a la configuracion
        rut_medico=rut_medico,
        nlp=NLPConfig(
            enabled=bool(nlp_cfg.get("enabled", True)),
            model=nlp_cfg.get("model", "es_core_news_sm"),
        ),
    )


def build_priorizacion_cfg(cfg: Dict[str, Any], anio: int, mes: int) -> tuple[SemaforoConfig, PrioritizationConfig]:
    # fmateluna: Se calcula dinámicamente el rango de 6 meses hacia atrás.
    meses_anteriores = [(mes - i - 1) % 12 + 1 for i in range(6)]
    meses_anteriores.reverse()  # Ordenar de más antiguo a más reciente

    semaforo = cfg.get("semaforo", {})
    prioritization = cfg.get("prioritization", {})

    smf_cfg = SemaforoConfig(
        meses=semaforo.get("meses", meses_anteriores),
        rn_ln_mes=semaforo.get("rn_ln_mes", 400),
        umbral_decorte=semaforo.get("umbral_decorte", 0.5),
        umbral_deanomalias=semaforo.get("umbral_deanomalias", 0.5),
        sort_values_by=semaforo.get("sort_values_by", "um"),
    )
    prio_cfg = PrioritizationConfig(
        ordenar_por=prioritization.get("ordenar_por", "Fecha"),
        umbral_de_priorizacion=prioritization.get("umbral_de_priorizacion", 0.94),
        output_filename=prioritization.get("output_filename", "smf_denuncias.csv"),
    )
    return smf_cfg, prio_cfg

# def prepare_for_excel_json(df: pd.DataFrame) -> pd.DataFrame:
#     """Prepara DataFrame para serialización JSON compatible con Excel"""
#     df_copy = df.copy()
#     num_cols = df_copy.select_dtypes(include="number").columns
#     for c in num_cols:
#         df_copy[c] = df_copy[c].map(lambda x: f"{x:.4f}".replace(".", ",") if pd.notnull(x) else "")
#     return df_copy

def procesa_reclamos(request: ReclamosRequest) :
    periodo_str = f"[PERIODO: {request.anio}-{request.mes:02d}]"
    rut_medico_str = f"para el rut_medico: {request.rut_medico}" if request.rut_medico else "para todos los médicos"
    reclamos_logger.info(f"{periodo_str} Inicia procesamiento de reclamos para el período: {request.anio}-{request.mes:02d} {rut_medico_str}.")

    base_path = os.path.dirname(os.path.abspath(__file__)) + '/' 

    """Ejecuta el pipeline de procesamiento de reclamos usando configuración por defecto."""
    config_path = f"{base_path}/config.yml"
    
    cfg_dict = load_config(config_path)
    adm_cfg = build_admisibilidad_cfg(cfg_dict,request.anio,request.mes, request.rut_medico)
    smf_cfg, prio_cfg = build_priorizacion_cfg(cfg_dict, request.anio, request.mes)

    # ---------- Load ----------
    reclamos_logger.info(f"{periodo_str} Inicia la carga de datos desde la base de datos.")
    adm = AdmisibilidadProcessor(adm_cfg)
    df, denuncias, relatos, detalle, lme = adm.load_all()
    reclamos_logger.info(f"{periodo_str} Carga de datos finalizada. Registros cargados: df_semaforo={len(df)}, denuncias={len(denuncias)}, relatos={len(relatos)}, detalle_uclm={len(detalle)}, lme={len(lme)}.")

    # ---------- Base df_to_semaforo post-processing from notebook ----------
    for col in ["propensity_score_rn", "propensity_score_umbrales", "propensity_score_iforest"]:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(int)
    # Dates
    if "fecha_emision" in df.columns:
        df["fecha_emision"] = pd.to_datetime(df["fecha_emision"], errors="coerce")

    # ---------- Denuncias preprocessing & month filter ----------
    denuncias_prep = adm.preprocess_denuncias(denuncias)
    denuncias_mes = adm.filter_denuncias_month(denuncias_prep)

    # ---------- Join relatos ----------
    denuncias_previas_relato = adm.build_denuncias_previas_relato(denuncias_mes, relatos)

    # ---------- Relato vacío condition ----------
    denuncias_previas_relato = adm.add_relato_vacio_condition(denuncias_previas_relato, denuncias_mes, relatos)

    # ---------- LME + detalle ----------
    lme_prep, detalle_prep = adm.prepare_lme_and_detalle(lme, detalle)
    lme_merged_final = adm.merge_lme_detalle_variants(lme_prep, detalle_prep)

    # ---------- LME with denuncias & admisibilidad conditions ----------
    denuncias_licencias = adm.lme_with_denuncias(lme_merged_final, denuncias_previas_relato)

    # ---------- Consolidate admisibilidad ----------
    denuncias_previas_relato = adm.consolidate_admisibilidad(denuncias_previas_relato, denuncias_licencias)

    # ---------- Priorización ----------
    reclamos_logger.info(f"{periodo_str} Inicia la etapa de priorización.")
    pr = PriorizacionProcessor(smf_cfg, prio_cfg)
    denuncias_semaforo = pr.run_prioritization(df, denuncias_previas_relato)
    reclamos_logger.info(f"{periodo_str} Priorización finalizada. Se generaron {len(denuncias_semaforo)} resultados.")

    # ---------- Output ----------
    # df_prepared = prepare_for_excel_json(denuncias_semaforo)
    
    reclamos_logger.info(f"{periodo_str} Finaliza procesamiento de reclamos para el período: {request.anio}-{request.mes:02d}. Se devuelven {len(denuncias_semaforo)} registros.")
    return denuncias_semaforo.to_dict(orient='records')