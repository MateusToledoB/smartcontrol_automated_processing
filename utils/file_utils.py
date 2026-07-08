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
    def update_data_xlsx_from_download(cls) -> str:
        storage_dir = os.path.join(settings.BASE_DIR, "data_storage")
        destino = os.path.join(storage_dir, "data.xlsx")

        arquivos = [
            os.path.join(storage_dir, nome)
            for nome in os.listdir(storage_dir)
            if nome.lower() != "data.xlsx" and not nome.startswith(".")
        ]
        if not arquivos:
            raise FileNotFoundError(f"Nenhum arquivo baixado encontrado em {storage_dir}")

        # O export do portal cai com o nome que o site escolhe (as vezes com
        # timestamp/sufixo de download duplicado) - pega sempre o mais recente.
        origem = max(arquivos, key=os.path.getmtime)

        if origem.lower().endswith(".xlsx"):
            if os.path.exists(destino):
                os.remove(destino)
            os.replace(origem, destino)
        else:
            # .xls (formato legado, engine xlrd) e .csv nao sao .xlsx so por
            # trocar a extensao - o conteudo precisa ser relido e reescrito.
            if origem.lower().endswith(".csv"):
                df = pd.read_csv(origem)
            else:
                df = pd.read_excel(origem, engine="xlrd")
            df.to_excel(destino, index=False, engine="openpyxl")
            os.remove(origem)

        cls.clear_cache()
        return destino

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
