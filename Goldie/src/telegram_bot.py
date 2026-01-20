import requests
import time
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, BOT_IDENTITY

class TelegramBot:
    """
    The Messenger 🕊️ (v2.1 - Timeout Proof)
    Handles Telegram commands specifically targeted at this bot.
    """
    def __init__(self):
        self.base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
        self.chat_id = TELEGRAM_CHAT_ID
        self.last_update_id = 0
        self.identity = BOT_IDENTITY.lower()
        
    def send_msg(self, text):
        """Sends a message with identity prefix."""
        try:
            formatted_text = f"[{self.identity.upper()}]\n{text}"
            url = f"{self.base_url}/sendMessage"
            payload = {"chat_id": self.chat_id, "text": formatted_text}
            requests.post(url, json=payload, timeout=10) # 🛠️ Increased timeout
        except Exception as e:
            # We fail silently here to avoid spamming the console
            pass 

    def get_latest_command(self):
        """
        Polls for commands.
        """
        try:
            url = f"{self.base_url}/getUpdates"
            params = {"offset": self.last_update_id + 1, "timeout": 1}
            
            # 🛠️ Increased timeout to 10s to handle slow Telegram API
            response = requests.get(url, params=params, timeout=10) 
            
            data = response.json()
            
            if not data.get("ok") or not data.get("result"):
                return None

            updates = data["result"]
            cmd_action = None
            
            for update in updates:
                self.last_update_id = update["update_id"]
                
                if "message" in update and "text" in update["message"]:
                    msg = update["message"]["text"].strip().lower()
                    sender_id = str(update["message"]["from"]["id"])
                    
                    if sender_id != self.chat_id:
                        continue
                        
                    parts = msg.split()
                    if not parts: continue
                    
                    base_cmd = parts[0]
                    
                    # 1. GLOBAL CALL
                    if base_cmd == "/assemble":
                        cmd_action = "status"
                    
                    # 2. TARGETED CALL
                    elif base_cmd == f"/{self.identity}":
                        if len(parts) > 1:
                            cmd_action = parts[1]
            
            return cmd_action

        except Exception as e:
            # Silence the timeout error to keep logs clean
            # print(f"⚠️ Telegram Poll Error: {e}") 
            return None