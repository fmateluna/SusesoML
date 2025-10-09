# main.py
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import yaml

from admisibilidad import (
    AdmisibilidadConfig,
    NLPConfig,
    AdmisibilidadProcessor,
)
from priorizacion import (
    PriorizacionProcessor,
    SemaforoConfig,
    PrioritizationConfig,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("watson-pipeline")


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_admisibilidad_cfg(cfg: Dict[str, Any]) -> AdmisibilidadConfig:
    paths = cfg.get("paths", {})
    encoding = cfg.get("encoding", {})
    csv_sep = cfg.get("csv_sep", {})
    filters = cfg.get("filters", {})
    nlp_cfg = cfg.get("nlp", {})

    return AdmisibilidadConfig(
        path_df_to_semaforo=paths["df_to_semaforo"],
        path_denuncias_pae=paths["denuncias_pae"],
        path_relatos=paths["relatos"],
        path_detalle_uclm=paths["detalle_uclm"],
        path_lme=paths["lme"],
        enc_relatos=encoding.get("relatos"),
        enc_detalle_uclm=encoding.get("detalle_uclm"),
        sep_denuncias_pae=csv_sep.get("denuncias_pae", "|"),
        sep_detalle_uclm=csv_sep.get("detalle_uclm", "|"),
        sep_relatos=csv_sep.get("relatos", ","),
        causal_homologada=filters.get("causal_homologada", "Denuncia a profesional emisor"),
        mes_a_revisar=filters.get("mes_a_revisar", 6),
        anio=filters.get("anio", 2025),
        nlp=NLPConfig(
            enabled=bool(nlp_cfg.get("enabled", True)),
            model=nlp_cfg.get("model", "es_core_news_sm"),
        ),
    )


def build_priorizacion_cfg(cfg: Dict[str, Any]) -> tuple[SemaforoConfig, PrioritizationConfig]:
    semaforo = cfg.get("semaforo", {})
    prioritization = cfg.get("prioritization", {})

    smf_cfg = SemaforoConfig(
        meses=semaforo.get("meses", [4, 5, 6]),
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


def main(config_path: str) -> None:
    cfg_dict = load_config(config_path)
    adm_cfg = build_admisibilidad_cfg(cfg_dict)
    smf_cfg, prio_cfg = build_priorizacion_cfg(cfg_dict)

    # ---------- Load ----------
    adm = AdmisibilidadProcessor(adm_cfg)
    df, denuncias, relatos, detalle, lme = adm.load_all()

    # ---------- Base df_to_semaforo post-processing from notebook ----------
    for col in ["propensity_score_rn", "propensity_score_umbrales", "propensity_score_iforest"]:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(int)
    # Dates
    if "fecha_emision" in df.columns:
        df["fecha_emision"] = pd.to_datetime(df["fecha_emision"], errors="coerce")

    logger.info("df_to_semaforo loaded with %d rows.", len(df))

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
    pr = PriorizacionProcessor(smf_cfg, prio_cfg)
    denuncias_semaforo = pr.run_prioritization(df, denuncias_previas_relato)

    # ---------- Output ----------
    out_path = Path(prio_cfg.output_filename).resolve()
    PriorizacionProcessor.export_to_csv_excel_friendly(denuncias_semaforo, str(out_path))
    logger.info("Pipeline completed. Output: %s", out_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Watson pipeline from YAML config.")
    parser.add_argument("--config", type=str, default="./standalone/reclamos/config.yml", help="Path to YAML config file.")
    args = parser.parse_args()
    main(args.config)
