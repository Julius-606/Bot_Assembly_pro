import requests
import time
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

class TelegramBot:
    """
    The Messenger 🕊️
    Handles Telegram commands and alerts synchronously.
    """
    def __init__(self):
        self.base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
        self.chat_id = TELEGRAM_CHAT_ID
        self.last_update_id = 0
        
    def send_msg(self, text):
        """Sends a simple message to the admin."""
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {"chat_id": self.chat_id, "text": text}
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            print(f"⚠️ Telegram Send Failed: {e}")

    def get_latest_command(self):
        """
        Polls for the latest command from the user.
        Returns: 'pause', 'resume', 'status', or None
        """
        try:
            url = f"{self.base_url}/getUpdates"
            params = {"offset": self.last_update_id + 1, "timeout": 1}
            response = requests.get(url, params=params, timeout=3)
            data = response.json()
            
            if not data.get("ok") or not data.get("result"):
                return None

            updates = data["result"]
            last_cmd = None
            
            for update in updates:
                self.last_update_id = update["update_id"]
                
                # Check if it's a message
                if "message" in update and "text" in update["message"]:
                    msg = update["message"]["text"].strip().lower()
                    sender_id = str(update["message"]["from"]["id"])
                    
                    # Security: Only accept commands from YOUR chat_id
                    if sender_id != self.chat_id:
                        continue
                        
                    if msg == "/pause": last_cmd = "pause"
                    elif msg == "/resume": last_cmd = "resume"
                    elif msg == "/status": last_cmd = "status"
            
            return last_cmd

        except Exception as e:
            print(f"⚠️ Telegram Poll Error: {e}")
            return None
