import os
import dotenv

class Settings():
    dotenv.load_dotenv()

    SHEET_ID_PROBLEMA_NO_EQUIPAMENTO: str = os.getenv('SHEET_ID_PROBLEMA_NO_EQUIPAMENTO')

    SHEET_ID_APONTAMENTO_IMPAR: str = os.getenv('SHEET_ID_APONTAMENTO_IMPAR')

    SHEET_ID_TEMPORARIOS: str = os.getenv('SHEET_ID_TEMPORARIOS')

    SHEET_ID_EXCECOES_VALIDAS: str = os.getenv('SHEET_ID_EXCECOES_VALIDAS')

    USER_MOTUS: str = os.getenv('USER_MOTUS')

    PASSWORD_MOTUS: str = os.getenv('PASS_MOTUS')

    URL_MOTUS: str = os.getenv('URL_MOTUS')

    SMARTSHEET_TOKEN: str = os.getenv('SMARTSHEET_TOKEN')

    URL_API_MAPPING_SITE: str = os.getenv('URL_API_MAPPING_SITE')

    USER_NAME_API_SITE_MAPPING: str = os.getenv('USER_NAME_API_SITE_MAPPING')

    PASSWORD_API_SITE_MAPPING: str = os.getenv('PASSWORD_API_SITE_MAPPING')
    

settings = Settings()