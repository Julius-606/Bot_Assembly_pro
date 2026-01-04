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

# Importing from the root config
from config import GOOGLE_CREDS, SHEET_URL, WORKSHEET_LOGS, USER_DEFAULT_MARKETS, DEFAULT_PARAMS, DRIVE_FOLDER_ID, DEFAULT_STRATEGY, MEMORY_FILENAME

class CloudManager:
    """
    The Brain 🧠
    Handles Google Sheets logging and Drive memory persistence.
    """
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
        self.load_state()

    def setup(self):
        try:
            scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
            
            # FIX: Parse the string into a dict!
            creds_dict = json.loads(GOOGLE_CREDS)
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            
            self.sheets_client = gspread.authorize(creds)
            self.drive_service = build('drive', 'v3', credentials=creds)
            print("   ☁️  Google Auth -> [SUCCESS]")
        except Exception as e:
            print(f"❌ Cloud Auth Failed: {e}")

    def load_state(self):
        try:
            if not self.drive_service: return
            
            # Escape single quotes in filename for the query
            query = f"name = '{MEMORY_FILENAME}' and '{DRIVE_FOLDER_ID}' in parents and trashed = false"
            results = self.drive_service.files().list(q=query, fields="files(id, name)").execute()
            items = results.get('files', [])

            if not items:
                print("⚠️ New Memory Created.")
                self.state = self.default_state.copy()
                self.state['status'] = "running"
                self.file_id = None
            else:
                self.file_id = items[0]['id']
                request = self.drive_service.files().get_media(fileId=self.file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False: status, done = downloader.next_chunk()
                
                fh.seek(0)
                self.state = json.loads(fh.read().decode('utf-8'))
                
                # Merge defaults to avoid key errors if you add new features later
                for k, v in self.default_state.items():
                    if k not in self.state: self.state[k] = v
                
                print(f"🧠 Memory Loaded. Balance: ${self.state.get('current_balance', 0)}")
                
        except Exception as e:
            print(f"❌ Load Failed: {e}")
            self.state = self.default_state.copy()

    def save_state(self):
        if not self.drive_service: return
        try:
            media = MediaIoBaseUpload(io.BytesIO(json.dumps(self.state, indent=2).encode('utf-8')), mimetype='application/json', resumable=True)
            if self.file_id:
                self.drive_service.files().update(fileId=self.file_id, media_body=media).execute()
            else:
                f = self.drive_service.files().create(body={'name': MEMORY_FILENAME, 'parents': [DRIVE_FOLDER_ID]}, media_body=media, fields='id').execute()
                self.file_id = f.get('id')
        except Exception as e:
            print(f"❌ Save Failed: {e}")

    def log_trade(self, trade):
        if not self.sheets_client: return
        try:
            sheet = self.sheets_client.open_by_url(SHEET_URL)
            try: ws = sheet.worksheet(WORKSHEET_LOGS)
            except: ws = sheet.add_worksheet(title=WORKSHEET_LOGS, rows=1000, cols=20)
            
            status_id = str(trade.get('ticket', 'UNKNOWN'))
            
            row = [
                status_id, 
                trade['strategy'], 
                trade['signal'], 
                trade['pair'],
                trade['open_time'], 
                trade['entry_price'], 
                trade['stop_loss_price'], 
                trade['take_profit_price'],
                trade['volume'], 
                trade.get('spread', 0),
                trade['exit_price'],
                trade.get('close_time', ''),
                trade['pnl'], 
                f"{self.state.get('current_balance', 0):.2f}"
            ]
            ws.append_row(row, value_input_option="USER_ENTERED")
        except Exception as e:
            print(f"❌ Log Failed: {e}")
