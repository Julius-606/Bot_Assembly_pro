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
    def __init__(self):
        self.sheets_client = None
        self.drive_service = None
        self.state = {}
        self.file_id = None
        
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
        try:
            # It's already a dict, so we use it directly!
            creds = Credentials.from_service_account_info(
                GOOGLE_CREDS_DICT,
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"
                ]
            )
            self.sheets_client = gspread.authorize(creds)
            self.drive_service = build('drive', 'v3', credentials=creds)
            
            # Use specific URL from config
            self.sheet_url = SHEET_URL
            print("   ☁️  Connected to Google Cloud!")
            
        except Exception as e:
            print(f"   ❌ Cloud Connection Failed: {e}")

    def load_memory(self):
        """
        Downloads memory.json from Drive.
        If not found, creates a fresh one.
        """
        print(f"   🧠 Syncing with Hive Mind ({MEMORY_FILENAME})...")
        try:
            # 1. Search for the file
            query = f"name = '{MEMORY_FILENAME}' and '{DRIVE_FOLDER_ID}' in parents and trashed = false"
            results = self.drive_service.files().list(q=query, fields="files(id, name)").execute()
            items = results.get('files', [])

            if not items:
                print("   ✨ No memory found. Creating fresh brain.")
                self.state = self.default_state
                self.save_memory(initial=True) # Create it
            else:
                # 2. Download it
                self.file_id = items[0]['id']
                request = self.drive_service.files().get_media(fileId=self.file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                
                fh.seek(0)
                content = fh.read().decode('utf-8')
                self.state = json.loads(content)
                print("   ✅ Memory Downloaded.")

        except Exception as e:
            print(f"   ⚠️ Memory Sync Error: {e}")
            self.state = self.default_state # Fallback

    def save_memory(self, initial=False):
        """
        Uploads current state to Drive.
        """
        try:
            file_metadata = {
                'name': MEMORY_FILENAME,
                'parents': [DRIVE_FOLDER_ID]
            }
            
            media = MediaIoBaseUpload(
                io.BytesIO(json.dumps(self.state, indent=4).encode('utf-8')),
                mimetype='application/json',
                resumable=True
            )

            if initial or not self.file_id:
                # Create new
                f = self.drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                self.file_id = f.get('id')
            else:
                # Update existing
                self.drive_service.files().update(
                    fileId=self.file_id,
                    media_body=media
                ).execute()
                
        except Exception as e:
            print(f"   ⚠️ Failed to save memory: {e}")

    def log_trade(self, trade_data, reason="OPEN"):
        """
        Logs a trade to the Google Sheet.
        """
        try:
            sheet = self.sheets_client.open_by_url(self.sheet_url)
            try:
                ws = sheet.worksheet(WORKSHEET_LOGS)
            except:
                print(f"   📝 Worksheet '{WORKSHEET_LOGS}' not found, creating it...")
                ws = sheet.add_worksheet(title=WORKSHEET_LOGS, rows=1000, cols=20)
                ws.append_row(["Ticket", "Strategy", "Signal", "Pair", "Log Time", "Time", "Entry", "SL", "TP", "Vol", "Spread", "Exit", "Close Time", "PnL", "Balance", "Reason"])
            
            # Sanitize data for JSON serialization/Sheets
            status_id = str(trade_data.get('ticket', 'UNKNOWN'))
            log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            row = [
                status_id, 
                str(trade_data.get('strategy', 'Unknown')), 
                str(trade_data.get('signal', 'Unknown')), 
                str(trade_data.get('pair', 'Unknown')),
                log_time,
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
        """Adds trade to local memory and syncs to cloud."""
        self.state['open_bot_trades'].append(trade)
        self.save_memory()

    def update_trade(self, ticket, data):
        """Updates a trade in memory (e.g., closing it)."""
        for i, t in enumerate(self.state['open_bot_trades']):
            if t['ticket'] == ticket:
                self.state['open_bot_trades'][i].update(data)
                # If closed, remove from active list? 
                # For safety, we keep them in 'open_bot_trades' until fully verified closed?
                # Actually, main.py handles the list logic usually. 
                # Let's just save.
                self.save_memory()
                return

    def close_trade_in_memory(self, ticket):
        """Removes trade from open_bot_trades."""
        self.state['open_bot_trades'] = [t for t in self.state['open_bot_trades'] if t['ticket'] != ticket]
        self.save_memory()