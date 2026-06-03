import os
import dotenv

class Settings():
    dotenv.load_dotenv()

    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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

    URL_PORTAL_GPSSA: str = os.getenv('URL_PORTAL_GPSSA')

    URL_ADMISSOES_ATIVAS: str = os.getenv('URL_ADMISSOES_ATIVAS')

    USER_PORTAL_GPSSA: str = os.getenv('USER_PORTAL_GPSSA')

    PASSWORD_PORTAL_GPSSA: str = os.getenv('PASSWORD_PORTAL_GPSSA')
    

settings = Settings()