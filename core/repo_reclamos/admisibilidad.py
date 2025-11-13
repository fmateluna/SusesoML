# admisibilidad.py
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Optional, Tuple, Dict, Any

import pandas as pd

from core.services import consulta_licencias_periodo, consulta_semaforo_reclamos, consulta_detalle_uclm, consulta_relatos, consulta_denuncias_pae

try:
    import spacy
except Exception:  # pragma: no cover
    spacy = None


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Migracion de csv/xlsx a Base de datos : Se comenta la funcion _read_tabular ya que ya no se utiliza
# def _read_tabular(path: str, sep: Optional[str] = None, encoding: Optional[str] = None) -> pd.DataFrame:
#     """
#     Read CSV or Excel depending on file extension. For CSV, pass sep/encoding.
#     """
#     lower = path.lower()
#     if lower.endswith(".xlsx") or lower.endswith(".xls"):
#         return pd.read_excel(path)
#     # default to CSV
#     kwargs: Dict[str, Any] = {}
#     if sep is not None:
#         kwargs["sep"] = sep
#     if encoding is not None:
#         kwargs["encoding"] = encoding
#     # safer for malformed lines
#     kwargs["on_bad_lines"] = "skip"
#     return pd.read_csv(path, **kwargs)


def clean_id_lic(id_lic) -> str:
    """
    Keep only digits and K/k for Chilean check digit patterns.
    """
    id_lic = str(id_lic)
    return re.sub(r"[^0-9Kk]", "", id_lic)


@dataclass
class NLPConfig:
    enabled: bool = True
    model: str = "es_core_news_sm"


@dataclass
class AdmisibilidadConfig:
    
    # Migracion de csv/xlsx a Base de datos : enc_detalle_uclm ya no es necesario
    # enc_detalle_uclm: Optional[str] = None

    # Migracion de csv/xlsx a Base de datos : sep_detalle_uclm ya no es necesario
    # sep_detalle_uclm: Optional[str] = "|"

    causal_homologada: str = "Denuncia a profesional emisor"
    
    mes_a_revisar: int = 6
    anio: int = 2025
    # fmateluna : Se agrega el rut_medico como parametro opcional
    rut_medico: Optional[str] = None

    # nlp: NLPConfig = NLPConfig()
    nlp: NLPConfig = field(default_factory=NLPConfig)



class AdmisibilidadProcessor:
    """
    Handles:
    - Load & preprocess denuncias/relatos/detalleUCLM/LME
    - NLP (optional) for detecting multiple professionals mentioned
    - Admisibilidad conditions:
        * Relato vacío
        * Licencia >= 5 años (no admisible)
        * LME médico ≠ médico denunciado (no admisible)
    - Produces 'denuncias_previas_relato' ready for priorización step
    """

    def __init__(self, cfg: AdmisibilidadConfig) -> None:
        self.cfg = cfg
        self._nlp = None

    # -------------------- Loading --------------------
    def load_all(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Returns (df_to_semaforo, denuncias, relatos, detalleUCLM, lme)
        """
        logger.info("Loading from DATABASE df_to_semaforo...")        
        # Se pasa el rut_medico a la consulta de semaforo
        # fmateluna : Se pasa el rut_medico a la consulta de semaforo
        df = self.consulta_base_semaforo(self.cfg.mes_a_revisar, self.cfg.anio, self.cfg.rut_medico)

        logger.info("Loading denuncias (PAE) from DATABASE...")
        denuncias = self.consulta_base_denuncias_pae(self.cfg.mes_a_revisar, self.cfg.anio)

        logger.info("Loading relatos from DATABASE...")
        relatos = self.consulta_base_relatos(self.cfg.mes_a_revisar, self.cfg.anio)

        logger.info("Loading detalle UCLM...")
        # fmateluna : Se reemplaza la lectura del CSV por una consulta a la base de datos
        detalle = self.consulta_base_detalle_uclm(self.cfg.mes_a_revisar, self.cfg.anio)

        logger.info("Loading From DataBase LME...")
        # fmateluna : Se reemplaza la lectura del CSV por una consulta a la base de datos
        lme = self.consulta_base_lme(self.cfg.mes_a_revisar, self.cfg.anio, self.cfg.rut_medico)

        return df, denuncias, relatos, detalle, lme
    
    # fmateluna : Se crea esta funcion para consultar el detalle de uclm
    def consulta_base_detalle_uclm(self, mes: int, anio: int) -> pd.DataFrame:
        data = consulta_detalle_uclm(anio=anio, mes=mes)
        df = pd.DataFrame(data)
        return df

    # fmateluna : Se crea esta funcion para consultar los relatos
    def consulta_base_relatos(self, mes: int, anio: int) -> pd.DataFrame:
        data = consulta_relatos(anio=anio, mes=mes)
        df = pd.DataFrame(data)
        # Migracion archivos a base de datos : Se renombra la columna 'folio_fui' a 'FUN_FOLIO' y 'relato' a 'FUN_RELATO' para compatibilidad.
        df = df.rename(columns={"folio_fui": "FUN_FOLIO", "relato": "FUN_RELATO"})
        return df

    # fmateluna : Se crea esta funcion para consultar las denuncias PAE
    def consulta_base_denuncias_pae(self, mes: int, anio: int) -> pd.DataFrame:
        data = consulta_denuncias_pae(anio=anio, mes=mes)
        df = pd.DataFrame(data)
        # Migracion archivos a base de datos : Se agrega la columna 'origen' con valor 'PAE' para mantener compatibilidad con la logica original del CSV.
        df["origen"] = "PAE"
        return df

    # fmateluna : Se agrega el rut_medico como opcional a la consulta
    def consulta_base_lme(self, mes: int, anio: int, rut_medico: Optional[str] = None) -> pd.DataFrame:    
        data = consulta_licencias_periodo(anio=anio, mes=mes, rut_medico=rut_medico)
        df = pd.DataFrame(data)
        return df        


    def consulta_base_semaforo(self, mes: int, anio: int, rut_medico: Optional[str] = None) -> pd.DataFrame:    
        # Se agrega el rut_medico a la consulta
        data = consulta_semaforo_reclamos(anio=anio, mes=mes, rut_medico=rut_medico)
        if not data:
            # Si la consulta a la base de datos no devuelve resultados,
            # se retorna un DataFrame vacío pero con las columnas esperadas.
            # Esto evita un KeyError en etapas posteriores del pipeline
            # cuando se intenta acceder a columnas que no existen en un DataFrame sin cabeceras.
            return pd.DataFrame(columns=[
                'id_lic', 'rut_medico', 'fecha_emision', 'propensity_score_rn', 
                'propensity_score_umbrales', 'propensity_score_iforest'
            ])
        df = pd.DataFrame(data)
        return df        

    # -------------------- NLP --------------------
    def _ensure_nlp(self) -> None:
        if not self.cfg.nlp.enabled:
            return
        if spacy is None:
            logger.warning("spaCy not installed; NLP disabled.")
            self.cfg.nlp.enabled = False
            return
        if self._nlp is None:
            try:
                self._nlp = spacy.load(self.cfg.nlp.model)
            except Exception as e:
                logger.warning("Could not load spaCy model '%s': %s. NLP disabled.",
                               self.cfg.nlp.model, e)
                self.cfg.nlp.enabled = False

    def count_mentions(self, df: pd.DataFrame, text_column: str,
                       person_thresh: int = 2, doctor_thresh: int = 2) -> pd.DataFrame:
        """
        Add columns marking multiple-person mentions and doctor token counts.
        If NLP disabled, returns df unchanged aside from required columns with zeros.
        """
        self._ensure_nlp()
        if not self.cfg.nlp.enabled or self._nlp is None:
            df = df.copy()
            df["num_personas"] = 0
            df["num_personas_NER"] = 0
            df["num_doctores"] = 0
            df["personas_sobre_umbral"] = 0
            df["doctores_sobre_umbral"] = 0
            return df

        people_counts, people_ner_counts, doctor_counts = [], [], []
        for text in df[text_column].astype(str):
            doc = self._nlp(text)
            people_ner = [ent.text for ent in doc.ents if ent.label_ == "PER"]
            doctors = [t.text.lower() for t in doc if t.text.lower() in ["doctor", "doctora", "dr.", "dra."]]
            people_counts.append(len(people_ner))
            people_ner_counts.append(len(set(people_ner)))
            doctor_counts.append(len(doctors))

        df = df.copy()
        df["num_personas"] = people_counts
        df["num_personas_NER"] = people_ner_counts
        df["num_doctores"] = doctor_counts
        df["personas_sobre_umbral"] = (df["num_personas"] >= person_thresh).astype(int)
        df["doctores_sobre_umbral"] = (df["num_doctores"] >= doctor_thresh).astype(int)
        return df

    # -------------------- Preprocess & filters --------------------
    def preprocess_denuncias(self, denuncias: pd.DataFrame) -> pd.DataFrame:
        d = denuncias.copy()
        print(d.head())
        print(d.columns)
        d["sancionado"] = d["tipo_sancion"].notna().astype(int)
        if "causal_homologada" in d.columns:
            d = d[d["causal_homologada"] == self.cfg.causal_homologada]
        # fmateluna : Si se especifica un rut_medico, se filtra por el
        if self.cfg.rut_medico:
            d = d[d["rut_medico"] == self.cfg.rut_medico]
        d["fecha_ingreso"] = pd.to_datetime(d["fecha_ingreso"], errors="coerce")
        d = d.reset_index(drop=True)
        logger.info("Denuncias preprocessed. Count: %d", len(d))
        return d

    def filter_denuncias_month(self, denuncias: pd.DataFrame) -> pd.DataFrame:
        start_date = pd.to_datetime(f'{self.cfg.anio}-{self.cfg.mes_a_revisar:02d}-01')
        end_date = start_date + pd.DateOffset(months=1)
        m = denuncias[(denuncias["fecha_ingreso"] >= start_date) &
                      (denuncias["fecha_ingreso"] < end_date)].copy()
        logger.info("Filtered denuncias for %s: %d rows", start_date.strftime("%B %Y"), len(m))
        return m

    # -------------------- Join relatos & first conditions --------------------
    def build_denuncias_previas_relato(
        self,
        denuncias_filtradas: pd.DataFrame,
        relatos: pd.DataFrame,
    ) -> pd.DataFrame:
        # Assumes relatos has 'FUN_FOLIO' (ID) & 'FUN_RELATO'
        print("DEBUG: Columnas de 'relatos' antes del merge:", relatos.columns)
        print("DEBUG: Columnas de 'denuncias_filtradas' antes del merge:", denuncias_filtradas.columns)
        merged = pd.merge(
            relatos, denuncias_filtradas,
            how="inner", left_on="FUN_FOLIO", right_on="folio_fui"
        )
        merged["no_admisible"] = ((merged["fecha_fui_analizado"].isna()) &
                                  (merged["fecha_cierre"].notna())).astype(int)
        cols_keep = ["folio_fui", "FUN_RELATO", "rut_medico", "fecha_ingreso", "sancionado", "no_admisible"]
        merged = merged[cols_keep].copy()

        # NLP mentions
        merged = self.count_mentions(merged, "FUN_RELATO")

        # Drop helper columns per original notebook step
        merged.drop(
            columns=["num_personas", "num_personas_NER", "num_doctores", "personas_sobre_umbral", "doctores_sobre_umbral"],
            inplace=True, errors="ignore"
        )
        logger.info("Built 'denuncias_previas_relato' with relato info.")
        return merged

    def add_relato_vacio_condition(
        self,
        denuncias_previas_relato: pd.DataFrame,
        denuncias_filtradas: pd.DataFrame,
        relatos: pd.DataFrame,
    ) -> pd.DataFrame:
        # Find denuncias without relato (left_only)
        ID_RELATOS = "FUN_FOLIO"
        left = pd.merge(
            denuncias_filtradas, relatos, how="left", left_on="folio_fui", right_on=ID_RELATOS, indicator=True
        )
        left_only = left[left["_merge"] == "left_only"].drop(columns=["_merge"])
        if "origen" in left_only.columns:
            left_only = left_only[left_only["origen"] == "PAE"]

        merged = denuncias_previas_relato.merge(
            left_only[[ID_RELATOS]],
            right_on=ID_RELATOS,
            left_on="folio_fui",
            how="left",
            indicator=True
        )
        out = denuncias_previas_relato.copy()
        out["no_admisible"] = (merged["_merge"] == "both").astype(int)
        logger.info("Applied 'relato vacío' condition.")
        return out

    # -------------------- LME <-> Detalle UCLM join --------------------
    def prepare_lme_and_detalle(self, lme: pd.DataFrame, detalleUCLM: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        lme = lme.copy()
        detalleUCLM = detalleUCLM.copy()

        # Filters
        # fmateluna : Si se especifica un rut_medico, se filtra por el
        if self.cfg.rut_medico:
            lme = lme[lme["rut_medico"] == self.cfg.rut_medico]
        if "dias_reposo" in lme.columns:
            lme = lme[lme["dias_reposo"] <= 365]
        if "cod_diagnostico_principal" in lme.columns:
            lme = lme[~lme["cod_diagnostico_principal"].isin(["U07.1", "U07.2"])]
        # Dates
        for c in ["fecha_emision", "fecha_recepcion_empleador"]:
            if c in lme.columns:
                lme[c] = pd.to_datetime(lme[c], errors="coerce")

        # Clean folios
        lme["clean_id_lic"] = lme["id_lic"].apply(clean_id_lic)
        detalleUCLM["clean_num_lic"] = detalleUCLM["NUM_LICENCIA"].apply(clean_id_lic)
        detalleUCLM["len_num_licencia"] = detalleUCLM["clean_num_lic"].astype(str).str.len()
        detalleUCLM = detalleUCLM[(detalleUCLM["len_num_licencia"] >= 8) & (detalleUCLM["len_num_licencia"] <= 10)].reset_index(drop=True)

        # Split by length
        detalleUCLM["num_lic_8"] = detalleUCLM["clean_num_lic"].where(detalleUCLM["len_num_licencia"] == 8)
        detalleUCLM["num_lic_9"] = detalleUCLM["clean_num_lic"].where(detalleUCLM["len_num_licencia"] == 9)
        detalleUCLM["num_lic_10"] = detalleUCLM["clean_num_lic"].where(detalleUCLM["len_num_licencia"] == 10)
        detalleUCLM.drop(columns=["clean_num_lic"], inplace=True, errors="ignore")

        # lme substrings
        lme["sub_8_inicio"] = lme["clean_id_lic"].str[:8]
        lme["sub_8_medio"] = lme["clean_id_lic"].str[1:9]
        lme["sub_8_final"] = lme["clean_id_lic"].str[2:10]
        lme["sub_9_inicio"] = lme["clean_id_lic"].str[:9]
        lme["sub_9_final"] = lme["clean_id_lic"].str[1:10]

        return lme, detalleUCLM

    def merge_lme_detalle_variants(self, lme: pd.DataFrame, detalleUCLM: pd.DataFrame) -> pd.DataFrame:
        """
        Applies the multiple merge cases and concatenates results.
        """
        merge_cases = [
            ("sub_8_inicio", "num_lic_8"),
            ("sub_8_medio", "num_lic_8"),
            ("sub_8_final", "num_lic_8"),
            ("sub_9_inicio", "num_lic_9"),
            ("sub_9_final", "num_lic_9"),
            ("clean_id_lic", "num_lic_10"),
        ]
        lme_list = [lme.merge(detalleUCLM, left_on=left, right_on=right, how="inner")
                    for left, right in merge_cases]
        merged_final = pd.concat(lme_list, ignore_index=True).drop_duplicates()
        logger.info("Merged LME with Detalle UCLM. Rows: %d", len(merged_final))
        return merged_final

    # -------------------- LME join with denuncias & conditions --------------------
    def lme_with_denuncias(
        self,
        lme_merged_final: pd.DataFrame,
        denuncias_previas_relato: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Join LME+Detalle with denuncias_previas_relato (by FUI_UCLM vs folio_fui), compute
        5-year old license condition and doctor mismatch.
        """
        # Ensure dates
        for c in ["fecha_ingreso", "fecha_emision"]:
            if c in lme_merged_final.columns:
                lme_merged_final[c] = pd.to_datetime(lme_merged_final[c], errors="coerce")

        # Base frame
        denuncia_lic = lme_merged_final[["id_lic", "rut_medico", "fecha_emision", "FUI_UCLM"]].merge(
            denuncias_previas_relato, left_on="FUI_UCLM", right_on="folio_fui", how="inner"
        )

        # 5 years condition
        denuncia_lic["fecha_ingreso"] = pd.to_datetime(denuncia_lic["fecha_ingreso"], errors="coerce")
        denuncia_lic["fecha_emision"] = pd.to_datetime(denuncia_lic["fecha_emision"], errors="coerce")
        denuncia_lic["no_admisible"] = (
            (denuncia_lic["fecha_ingreso"] - denuncia_lic["fecha_emision"]) >= timedelta(days=5 * 365)
        ).astype(int)

        # LME médico must match denunciado (if not, no_admisible = 1)
        # In the merged DF, LME's doctor is 'rut_medico_x' after further merges; here it's 'rut_medico' vs 'rut_medico_y'
        # To keep consistent with original logic, rename explicitly:
        denuncia_lic = denuncia_lic.rename(columns={"rut_medico_x": "rut_medico_lme"}) if "rut_medico_x" in denuncia_lic.columns else denuncia_lic
        denuncia_lic = denuncia_lic.rename(columns={"rut_medico_y": "rut_medico_den"}) if "rut_medico_y" in denuncia_lic.columns else denuncia_lic
        if "rut_medico_lme" not in denuncia_lic.columns:
            denuncia_lic["rut_medico_lme"] = denuncia_lic.get("rut_medico")

        if "rut_medico_den" not in denuncia_lic.columns:
            denuncia_lic["rut_medico_den"] = denuncia_lic.get("rut_medico")

        denuncia_lic["no_admisible"] = (denuncia_lic["rut_medico_lme"] != denuncia_lic["rut_medico_den"]).astype(int)

        # If a FUI appears with multiple doctors, mark not admissible
        duplicated_fui = denuncia_lic[denuncia_lic.duplicated(subset=["FUI_UCLM"], keep=False)]["FUI_UCLM"].unique()
        duplicated_fui_df = denuncia_lic[denuncia_lic["FUI_UCLM"].isin(duplicated_fui)].copy()
        for fui in duplicated_fui:
            subset = duplicated_fui_df[duplicated_fui_df["FUI_UCLM"] == fui]
            if subset["rut_medico_lme"].nunique() > 1:
                denuncia_lic.loc[denuncia_lic["FUI_UCLM"] == fui, "no_admisible"] = 1

        logger.info("Applied LME-related admisibilidad conditions.")
        return denuncia_lic

    def consolidate_admisibilidad(
        self,
        denuncias_previas_relato: pd.DataFrame,
        denuncias_licencias: pd.DataFrame
    ) -> pd.DataFrame:
        merged = denuncias_previas_relato.merge(
            denuncias_licencias[["folio_fui", "no_admisible"]],
            on="folio_fui", how="left", suffixes=("", "_licencias")
        )
        merged["no_admisible"] = merged.apply(
            lambda r: 1 if r.get("no_admisible_licencias", 0) == 1 else r.get("no_admisible", 0), axis=1
        )
        merged.drop(columns=["no_admisible_licencias"], inplace=True, errors="ignore")
        merged.drop_duplicates(subset=["folio_fui"], inplace=True)
        # Remove relato text (as original)
        merged.drop(columns=["FUN_RELATO"], inplace=True, errors="ignore")
        logger.info("Consolidated admisibilidad across conditions.")
        return merged
