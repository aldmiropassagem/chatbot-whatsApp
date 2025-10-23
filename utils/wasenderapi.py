import requests

class WaSenderAPI:
    def __init__(self, base_url="https://wasenderapi.com/api/"):
        self.base_url = base_url

    def enviar_mensagem(self, numero: str, mensagem: str, instance: str, token: str):
        """Envia mensagem via WaSenderAPI"""
        url = f"{self.base_url}/message/sendText/{instance}"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
        payload = {"number": numero, "text": mensagem}

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            print("✅ Mensagem enviada com sucesso:", response.json())
        except requests.exceptions.RequestException as e:
            print("❌ Erro ao enviar mensagem:", e)
