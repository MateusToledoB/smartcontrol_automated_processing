import requests
import json
from datetime import datetime

class TeamsWebhookClient:
    WEBHOOK_URL = "https://gpssacombr.webhook.office.com/webhookb2/e9bbf8e0-3f0d-4680-a136-ab5da0d0f25c@428525d9-23bd-4f8c-afa2-5600f401f326/IncomingWebhook/d7c04b6dfb78434f87468f87d59be168/e9c74bdd-6c85-497f-9dee-c0b817466d2c/V2da9sq6bNrqmf5wpokggzegupR_sa7Lg2KARM-i9jktY1"

    @staticmethod
    def send_alert(project_name: str, mensagem: str):
        date_now = datetime.now().strftime("%d/%m/%Y - %H:%M")
        
        # Monta a string no padrão solicitado
        body_message = f"{date_now} - {project_name} - \n{mensagem}"

        payload = {
            "text": body_message
        }
        
        headers = {
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                TeamsWebhookClient.WEBHOOK_URL,
                data=json.dumps(payload),
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                print(f"[Teams] Alerta de '{project_name}' enviado com sucesso.")
            else:
                print(f"[Teams] Erro ao enviar: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"[Teams] Erro de conexão ao tentar enviar alerta: {e}")