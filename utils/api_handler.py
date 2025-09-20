import requests
import json
from datetime import datetime
from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL
import logging

class DeepSeekAPIHandler:
    """
    Manejador para la API de DeepSeek. Permite enviar solicitudes y obtener respuestas del modelo.
    """
    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.base_url = DEEPSEEK_API_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def generate_response(self, system_prompt, user_input):
        """
        Envía una solicitud al modelo DeepSeek y retorna la respuesta generada.
        Args:
            system_prompt (str): Mensaje de sistema para el modelo.
            user_input (str): Consulta del usuario.
        Returns:
            str | None: Respuesta generada o None si hay error.
        """
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            "temperature": 0.1,
            "max_tokens": 500,
            "top_p": 0.9
        }

        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                data=json.dumps(payload),
                timeout=30
            )
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                print(f"API Error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Connection Error: {str(e)}")
            return None

    def normalize_text(self, text: str) -> str | None:
        """
        Normaliza un texto en español corrigiendo ortografía y puntuación
        sin alterar su intención ni agregar contenido nuevo. Devuelve solo
        el texto corregido, sin prefijos ni explicaciones.

        Args:
            text (str): Texto original del usuario.

        Returns:
            str | None: Texto normalizado o None en caso de error.
        """
        system_prompt = (
            "Eres un corrector ortográfico de español. Corrige ortografía, acentos y puntuación "
            "sin cambiar el significado ni la intención del texto. Devuelve únicamente el texto corregido, "
            "sin comentarios adicionales."
        )
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            "temperature": 0.0,
            "max_tokens": 300,
            "top_p": 0.9
        }
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                data=json.dumps(payload),
                timeout=20
            )
            if response.status_code == 200:
                out = response.json()['choices'][0]['message']['content']
                # Asegurar que no vengan etiquetas inesperadas
                return out.strip()
            else:
                logging.warning(f"Normalize API Error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logging.warning(f"Normalize Connection Error: {str(e)}")
            return None