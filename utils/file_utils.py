import os
from datetime import timedelta
import pandas as pd
from core.settings import settings


class FileUtils:
    _df_cache: pd.DataFrame | None = None

    @classmethod
    def load_srh_df(cls) -> pd.DataFrame:
        if cls._df_cache is None:
            path = os.path.join(settings.BASE_DIR, "data_storage", "data.xlsx")
            if not os.path.exists(path):
                raise FileNotFoundError(f"Arquivo não encontrado: {path}")
            cls._df_cache = pd.read_excel(path, engine="openpyxl")
        return cls._df_cache

    @classmethod
    def clear_cache(cls) -> None:
        cls._df_cache = None

    @classmethod
    def validate_id_mrh(cls, id_mrh: str, cr_number: str, data_registro: str) -> str:
        df = cls.load_srh_df()
        row = df[df["ID MRH"].astype(str) == str(id_mrh)]
        if row.empty:
            return "ID não encontrado"
        row = row.iloc[0]
        if cr_number not in str(row["CR"]):
            return "CR não corresponde"
        data       = pd.to_datetime(data_registro, format="%d/%m/%Y")
        dt_criacao = pd.to_datetime(row["DT CRIAÇÃO"], dayfirst=True)
        dt_limite  = pd.to_datetime(row["DT LIMITE"], dayfirst=True)
        if not (dt_criacao <= data <= dt_limite + timedelta(days=7)):
            return "Data fora do período"
        return "Aprovado"
