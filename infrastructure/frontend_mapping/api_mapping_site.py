from core.settings import settings
import requests
from datetime import datetime, timedelta
from utils.time_utils import TimeUtils

url = settings.URL_API_MAPPING_SITE

def send_mapping_data(data):
    payload = {
        "user": settings.USER_NAME_API_SITE_MAPPING,
        "password": settings.PASSWORD_API_SITE_MAPPING,
    }
    if data:
        payload.update(data)

    try:
        
        response = requests.post(url, json=payload, timeout=20)
    except requests.RequestException as e:
        print(f"Erro ao enviar dados para a API de mapeamento: {e}")

def send_execution_mapping(
    automation_name: str,
    titulo: str,
    affected_rows: int,
    start_time: datetime,
    running: bool
) -> datetime:
    called_at = datetime.now()
    payload = {
        "automation_name": automation_name,
        "titulo": titulo,
        "ultima_execucao": called_at.strftime("%d/%m/%Y %H:%M:%S"),
        "affected_rows": str(affected_rows),
        "tempo_execucao": TimeUtils.format_elapsed(start_time, called_at),
        "proxima_execucao": "Running" if running else (called_at + timedelta(minutes=5)).strftime("%d/%m/%Y %H:%M:%S"),
    }
    send_mapping_data(payload)
    return called_at
