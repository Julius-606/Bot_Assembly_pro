import json
import os
import gspread 
from datetime import datetime
from google.oauth2.service_account import Credentials

# Import configs
from config import (
    GOOGLE_CREDS, 
    SHEET_URL, 
    WORKSHEET_LOGS, 
    USER_DEFAULT_MARKETS, 
    DEFAULT_STRATEGY, 
    MEMORY_FILENAME
)

class CloudManager:
    """
    The Brain 🧠 (Hybrid Edition)
    """
    def __init__(self):
        self.sheets_client = None
        self.state = {}
        self.memory_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), MEMORY_FILENAME)
        
        self.default_state = {
            "status": "stopped",
            "current_balance": 0.0,
            "active_strategy": DEFAULT_STRATEGY,
            "active_pairs": USER_DEFAULT_MARKETS,
            "strategy_params": {}, # Empty here, strategy class has defaults
            "open_bot_trades": [], 
            "trade_history": [],
            "last_update_id": 0
        }
        
        self.setup_cloud()
        self.load_memory()

    def setup_cloud(self):
        try:
            creds_dict = json.loads(GOOGLE_CREDS)
            creds = Credentials.from_service_account_info(
                creds_dict,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            self.sheets_client = gspread.authorize(creds)
            print("   ☁️  Connected to Google Sheets.")
        except Exception as e:
            print(f"   ⚠️ Cloud Setup Failed: {e}")

    def load_memory(self):
        print(f"   📥 Loading Memory from Disk ({self.memory_path})...")
        if os.path.exists(self.memory_path):
            try:
                with open(self.memory_path, 'r') as f:
                    self.state = json.load(f)
                print("   🧠 Memory Loaded Successfully.")
            except Exception as e:
                print(f"   ⚠️ Corrupt Memory File: {e}. Starting fresh.")
                self.state = self.default_state
                self.save_memory()
        else:
            print("   🆕 No local memory found. Creating fresh brain.")
            self.state = self.default_state
            self.save_memory()

    def save_memory(self):
        try:
            with open(self.memory_path, 'w') as f:
                json.dump(self.state, f, indent=4)
        except Exception as e:
            print(f"   ⚠️ Save Memory Failed: {e}")

    def register_trade(self, trade_data):
        self.state['open_bot_trades'].append(trade_data)
        self.save_memory()

    def deregister_trade(self, ticket):
        self.state['open_bot_trades'] = [t for t in self.state['open_bot_trades'] if t['ticket'] != ticket]
        self.save_memory()

    def log_trade(self, trade, reason="OPEN"):
        if not self.sheets_client: 
            print("   ⚠️ Logger: No Sheets Client available!")
            return
            
        try:
            print(f"   📝 Logger: Writing to Sheets...")
            sheet = self.sheets_client.open_by_url(SHEET_URL)
            try: ws = sheet.worksheet(WORKSHEET_LOGS)
            except: 
                # Removed "Log Time" from header
                ws = sheet.add_worksheet(title=WORKSHEET_LOGS, rows=1000, cols=20)
                ws.append_row(["Ticket", "Strategy", "Signal", "Pair", "Open Time", "Entry", "SL", "TP", "Vol", "Spread", "Exit", "Close Time", "PnL", "Balance", "Reason"])
            
            status_id = str(trade.get('ticket', 'UNKNOWN'))
            # log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # Removed

            row = [
                status_id, 
                str(trade.get('strategy', 'Unknown')), 
                str(trade.get('signal', 'Unknown')), 
                str(trade.get('pair', 'Unknown')),
                # log_time, # Removed
                str(trade.get('open_time', '')), 
                float(trade.get('entry_price', 0)), 
                float(trade.get('stop_loss_price', 0)), 
                float(trade.get('take_profit_price', 0)),
                float(trade.get('volume', 0)), 
                float(trade.get('spread', 0)),
                float(trade.get('exit_price', 0)),
                str(trade.get('close_time', '')),
                float(trade.get('pnl', 0)), 
                f"{self.state.get('current_balance', 0)}",
                str(reason)
            ]
            ws.append_row(row)
            print(f"   ✅ Logged trade {status_id} to Cloud.")
        except Exception as e:
            print(f"   ❌ Logger Failed: {e}")