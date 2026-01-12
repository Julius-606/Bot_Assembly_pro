import json
import io
import time
import requests
import gspread 
import pandas as pd
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

# Import the pre-parsed DICT from config
from config import (
    GOOGLE_CREDS_DICT, SHEET_URL, WORKSHEET_LOGS, USER_DEFAULT_MARKETS, 
    DEFAULT_PARAMS, DRIVE_FOLDER_ID, DEFAULT_STRATEGY, MEMORY_FILENAME
)

class CloudManager:
    """
    The Cloud Manager ☁️
    Handles Google Sheets (Logs) and Google Drive (Memory JSON).
    """
    def __init__(self):
        self.sheets_client = None
        self.drive_service = None
        self.state = {}
        self.file_id = None
        
        # Default Memory Structure
        self.default_state = {
            "status": "stopped",
            "current_balance": 0.0,
            "active_strategy": DEFAULT_STRATEGY,
            "active_pairs": USER_DEFAULT_MARKETS,
            "strategy_params": DEFAULT_PARAMS,
            "open_bot_trades": [], 
            "trade_history": [],
            "last_update_id": 0
        }
        
        self.setup()
        self.load_memory()

    def setup(self):
        """Authenticates with Google."""
        try:
            # It's already a dict, so we use it directly!
            creds = Credentials.from_service_account_info(
                GOOGLE_CREDS_DICT, 
                scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            )
            self.sheets_client = gspread.authorize(creds)
            self.drive_service = build('drive', 'v3', credentials=creds)
            
            # Verify connection
            self.sheet_url = SHEET_URL
            print("   ☁️  Connected to Google Cloud!")
            
        except Exception as e:
            print(f"   ❌ Cloud Config Error: {e}")

    def load_memory(self):
        """Loads memory from local JSON file."""
        try:
            with open(MEMORY_FILENAME, "r") as f:
                self.state = json.load(f)
            print(f"   🧠 Syncing with Hive Mind ({MEMORY_FILENAME})...")
            print("   ✅ Memory Downloaded.")
        except FileNotFoundError:
            print("   🧠 No memory file found. Starting fresh.")
            self.state = self.default_state
            self.save_memory()
        except Exception as e:
            print(f"   ⚠️ Memory Read Error: {e}")
            self.state = self.default_state

    def save_memory(self):
        """Saves current state to local JSON file."""
        try:
            with open(MEMORY_FILENAME, "w") as f:
                json.dump(self.state, f, indent=4)
        except Exception as e:
            print(f"   ❌ Failed to save memory: {e}")

    def log_trade(self, trade_data, reason="CLOSED"):
        """Logs a trade event to Google Sheets."""
        try:
            sheet = self.sheets_client.open_by_url(self.sheet_url)
            ws = sheet.worksheet(WORKSHEET_LOGS)
            
            # Ensure no None values
            row = [
                str(trade_data.get('ticket', '')),
                str(trade_data.get('strategy', '')),
                str(trade_data.get('signal', '')),
                str(trade_data.get('pair', '')),
                str(trade_data.get('open_time', '')),
                float(trade_data.get('entry_price', 0)),
                float(trade_data.get('stop_loss_price', 0)),
                float(trade_data.get('take_profit_price', 0)),
                float(trade_data.get('volume', 0)),
                float(trade_data.get('spread', 0)),
                float(trade_data.get('exit_price', 0)),
                str(trade_data.get('close_time', '')),
                float(trade_data.get('pnl', 0)), 
                "0.00", # Balance placeholder if not tracking
                str(reason)
            ]
            
            ws.append_row(row)
            print(f"   📝 Logged {reason} for {trade_data.get('pair')}")

        except Exception as e:
            print(f"   ❌ Logging Failed: {e}")

    def register_trade(self, trade):
        """Adds trade to local memory and syncs."""
        self.state['open_bot_trades'].append(trade)
        self.save_memory()

    def deregister_trade(self, ticket):
        """Removes a trade from memory (used when closed)."""
        # Filter out the trade with the matching ticket
        original_count = len(self.state['open_bot_trades'])
        self.state['open_bot_trades'] = [t for t in self.state['open_bot_trades'] if t['ticket'] != ticket]
        
        if len(self.state['open_bot_trades']) < original_count:
            self.save_memory()
            # print(f"   🗑️ Trade {ticket} removed from memory.")

    def update_trade(self, ticket, data):
        """Updates a trade in memory (e.g., changing SL/TP)."""
        found = False
        for i, t in enumerate(self.state['open_bot_trades']):
            if t['ticket'] == ticket:
                self.state['open_bot_trades'][i].update(data)
                found = True
                break
        
        if found:
            self.save_memory()

    def close_trade_in_memory(self, ticket, exit_data):
        """
        Moves a trade from 'open_bot_trades' to 'trade_history'.
        (Helper method if you want to keep local history).
        """
        trade_to_close = None
        # 1. Find and Remove from Open
        new_open_list = []
        for t in self.state['open_bot_trades']:
            if t['ticket'] == ticket:
                trade_to_close = t
            else:
                new_open_list.append(t)
        
        self.state['open_bot_trades'] = new_open_list

        # 2. Add to History with Exit Data
        if trade_to_close:
            trade_to_close.update(exit_data)
            self.state['trade_history'].append(trade_to_close)
            
            # Keep history small? (Optional: Limit to last 100)
            if len(self.state['trade_history']) > 100:
                self.state['trade_history'].pop(0)

            self.save_memory()

    def get_open_trade_tickets(self):
        """Returns a list of currently open ticket numbers."""
        return [t['ticket'] for t in self.state.get('open_bot_trades', [])]