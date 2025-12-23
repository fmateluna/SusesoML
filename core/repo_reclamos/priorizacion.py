# priorizacion.py
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional
import os
import numpy as np
import pandas as pd

import logging

from core.services import consulta_semaforo
reclamos_logger = logging.getLogger('reclamos_logger')


@dataclass
class SemaforoConfig:
    meses: List[int]
    rn_ln_mes: int = 400
    umbral_decorte: float = 0.5
    umbral_deanomalias: float = 0.5
    sort_values_by: str = "um"


@dataclass
class PrioritizationConfig:
    ordenar_por: str = "Fecha"  # or "Priorización"
    umbral_de_priorizacion: float = 0.94
    output_filename: str = "smf_denuncias.csv"


class PriorizacionProcessor:
    """
    Implements semáforo metrics and combines with denuncias to produce a prioritized CSV.
    """

    def __init__(self, smf_cfg: SemaforoConfig, prio_cfg: PrioritizationConfig) -> None:
        self.smf_cfg = smf_cfg
        self.prio_cfg = prio_cfg

    # -------------------- Semáforo --------------------
    def semaforoWatson(
        self,
        df: pd.DataFrame,
        mes: Optional[int] = None,
        anio: Optional[int] = None,
        show_results: Optional[int] = None,
        sort_values_by: Optional[str] = None,
    ) -> pd.DataFrame:
        sort_values_by = sort_values_by or self.smf_cfg.sort_values_by

        # Si el DataFrame de entrada está vacío, retornar un DataFrame vacío con las columnas esperadas
        if df.empty:
            return pd.DataFrame(columns=[
                "rut_medico", "n_lic", "rn", "um", "an", "smf_rn", "smf_um", "smf_an"
            ])

        # Ensure datetime
        df = df.copy()
        df["fecha_emision"] = pd.to_datetime(df["fecha_emision"], errors="coerce")

        # Filters
        df_f = df.copy()
        if mes is not None:
            df_f = df_f[df_f["fecha_emision"].dt.month == mes]
        if anio is not None:
            df_f = df_f[df_f["fecha_emision"].dt.year == anio]

        # Thresholds
        um = (
            df_f[df_f["propensity_score_umbrales"] >= self.smf_cfg.umbral_decorte]
            .groupby("rut_medico")
            .size()
            .reset_index(name="um")
        )
        an = (
            df_f[df_f["propensity_score_iforest"] >= self.smf_cfg.umbral_deanomalias]
            .groupby("rut_medico")
            .size()
            .reset_index(name="an")
        )

        # Aggregate
        smf = (
            df_f.groupby("rut_medico")
            .agg(
                n_lic=("rut_medico", "count"),
                rn=("propensity_score_rn", "sum"),
            )
            .reset_index()
            .sort_values(by="n_lic", ascending=False)
        )

        smf = smf.merge(um, on="rut_medico", how="left")
        smf = smf.merge(an, on="rut_medico", how="left")
        smf["um"] = smf["um"].fillna(0).astype(int)
        smf["an"] = smf["an"].fillna(0).astype(int)

        # Proportions
        smf["smf_rn"] = smf.apply(
            lambda r: 1 if r["n_lic"] >= self.smf_cfg.rn_ln_mes else (r["rn"]) / r["n_lic"],
            axis=1,
        )
        denom_um = (smf["n_lic"] - smf["rn"]).replace({0: np.nan})
        smf["smf_um"] = smf["um"] / denom_um
        denom_an = (smf["n_lic"] - smf["rn"] - smf["um"]).replace({0: np.nan})
        smf["smf_an"] = smf["an"] / denom_an

        smf = smf.fillna(0)
        smf = smf.sort_values(by=sort_values_by, ascending=False)

        # Convert floats that are whole numbers to Int64
        for col in smf.select_dtypes(include=["float"]).columns:
            if len(smf) > 0 and np.all(np.mod(smf[col], 1) == 0):
                smf[col] = smf[col].astype("Int64")

        if show_results is not None:
            return smf.head(show_results)
        return smf

    import os
    import pandas as pd
    from typing import List, Optional

    def resumenMensualMedicos(
        self,
        df: pd.DataFrame,
        meses: List[int],
        anio: Optional[int] = None,
        sort_priority: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        if not meses:
            raise ValueError("Debes especificar al menos un mes.")

        df_medicos = pd.DataFrame({"rut_medico": df["rut_medico"].dropna().unique()})
        pieces = []
        for m in meses:
            #Esto lo puedo sacar de la tabla semaforo
            # mdf = self.semaforoWatson(df, mes=m, anio=anio, show_results=None)
            resultados = consulta_semaforo(rango=f"{anio}-{m:02d}", rut_medico=None)
            mdf = pd.DataFrame(resultados)
            prefix = f"m{m}_"
            mdf = mdf.add_prefix(prefix)
            # Corrige el rename para que coincida con el prefijo completo
            full_rut_col = f"{prefix}rut_medico"
            if full_rut_col in mdf.columns:
                mdf = mdf.rename(columns={full_rut_col: "rut_medico"})
            pieces.append(mdf)

        out = df_medicos.copy()
        for mdf in pieces:
            out = out.merge(mdf, on="rut_medico", how="left")
        out = out.fillna(0)

        if sort_priority is None:
            sort_priority = []
            for m in sorted(meses, reverse=True):
                sort_priority.extend([
                    f"m{m}_semaforo_an",
                    f"m{m}_semaforo_um",
                    f"m{m}_semaforo_rn",
                ])
            sort_priority = [c for c in sort_priority if c in out.columns]
        if sort_priority:
            out = out.sort_values(by=sort_priority, ascending=False)
        return out

    def unir_denuncias_con_semaforo(
        self,
        df_denuncias: pd.DataFrame,
        df_semaforo: pd.DataFrame,
        columnas_basicas: Optional[list] = None
    ) -> pd.DataFrame:
        columnas_basicas = columnas_basicas or ["folio_fui", "rut_medico", "fecha_ingreso", "sancionado", "no_admisible"]

        df = df_denuncias[columnas_basicas].merge(df_semaforo, on="rut_medico", how="left").fillna(0)

        smf_cols = [c for c in df.columns if c.startswith("m") and ("_smf_rn" in c or "_smf_um" in c or "_smf_an" in c)]
        cat_cols = []
        for col in smf_cols:
            cat_col = f"{col}_cat"
            # Aveces los valores de pd.cut vienen con valores NaN por eso agregue esto
            cut_series = pd.cut(
                df[col],
                bins=[-0.01, 0.5, 0.8, 1.01],
                labels=[1, 2, 4],
                include_lowest=True
            )
            df[cat_col] = cut_series.cat.add_categories([0]).fillna(0).astype(int)
            cat_cols.append(cat_col)

        df["ptje_prio"] = 0.0
        for col in smf_cols:
            df[f"{col}_cat"] = df[f"{col}_cat"].astype(int)
            df["ptje_prio"] += df[col].astype(float) * df[f"{col}_cat"]

        df = df.drop(columns=cat_cols, errors="ignore")
        return df

    # -------------------- Export --------------------
    @staticmethod
    def export_to_csv_excel_friendly(df: pd.DataFrame, filename: str) -> None:
        df_copy = df.copy()
        # Ensure date formatting is friendly (Excel often auto-localizes)
        num_cols = df_copy.select_dtypes(include="number").columns
        for c in num_cols:
            # Keep 4 decimals and convert dot to comma for locales using comma
            df_copy[c] = df_copy[c].map(lambda x: f"{x:.4f}".replace(".", ",") if pd.notnull(x) else "")
        df_copy.to_csv(filename, index=False, sep=";", encoding="latin-1")
        reclamos_logger.info("Exported CSV to %s", filename)
        return df_copy

    # -------------------- Orchestration --------------------
    def run_prioritization(
        self,
        df_base: pd.DataFrame,
        denuncias_previas_relato: pd.DataFrame
    ) -> pd.DataFrame:
        mes_actual =  pd.Timestamp.now().month
        anio_actual = pd.Timestamp.now().year

        smf = self.resumenMensualMedicos(
            df_base,
            meses=[mes_actual],
            anio=anio_actual
        )
        df = self.unir_denuncias_con_semaforo(denuncias_previas_relato, smf)

        if self.prio_cfg.ordenar_por == "Priorización":
            df.sort_values(by="ptje_prio", ascending=False, inplace=True)
        else:
            df.sort_values(by="fecha_ingreso", ascending=True, inplace=True)

        df["decision"] = np.where(df["ptje_prio"] > self.prio_cfg.umbral_de_priorizacion, "Priorizar", "sin decision")
        df["no_admisible"] = df["no_admisible"].replace({1: "No admisible", 0: "sin decision"})
        df["sancionado"] = df["sancionado"].replace({1: "Si", 0: "No"})
        return df
