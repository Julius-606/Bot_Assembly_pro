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

# Import configs
from config import (
    GOOGLE_CREDS, 
    SHEET_URL, 
    WORKSHEET_LOGS, 
    USER_DEFAULT_MARKETS, 
    DEFAULT_PARAMS, 
    DRIVE_FOLDER_ID, 
    DEFAULT_STRATEGY, 
    MEMORY_FILENAME
)

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
            "open_bot_trades": [], # The Flight Recorder list
            "trade_history": [],
            "last_update_id": 0
        }
        
        self.setup()
        self.load_memory()

    def setup(self):
        try:
            creds_dict = json.loads(GOOGLE_CREDS)
            creds = Credentials.from_service_account_info(
                creds_dict,
                scopes=[
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive'
                ]
            )
            self.sheets_client = gspread.authorize(creds)
            self.drive_service = build('drive', 'v3', credentials=creds)
            
            print("   ☁️  Connected to Google Cloud.")
            print(f"   📧 CRITICAL: Share '{SHEET_URL}' with:")
            print(f"      {creds.service_account_email}")
            
        except Exception as e:
            print(f"   ⚠️ Cloud Setup Failed: {e}")
            # We don't exit here, we allow the bot to run in 'offline' mode if needed,
            # but memory loading will be skipped.

    def load_memory(self):
        """Loads state from Google Drive JSON file"""
        # 🛡️ SAFETY CHECK: Don't try to use the phone if there's no signal.
        if not self.drive_service:
            print("   ⚠️ Cloud Offline: Using default temporary memory.")
            self.state = self.default_state
            return

        print(f"   📥 Downloading Memory ({MEMORY_FILENAME})...")
        try:
            # Search for file
            results = self.drive_service.files().list(
                q=f"name='{MEMORY_FILENAME}' and '{DRIVE_FOLDER_ID}' in parents",
                fields="files(id, name)"
            ).execute()
            items = results.get('files', [])

            if not items:
                print("   🆕 No memory found. Creating fresh brain.")
                self.state = self.default_state
                self.save_memory()
                return

            self.file_id = items[0]['id']
            request = self.drive_service.files().get_media(fileId=self.file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            fh.seek(0)
            self.state = json.load(fh)
            print("   🧠 Memory Loaded.")
        except Exception as e:
            print(f"   ⚠️ Load Memory Failed: {e}")
            self.state = self.default_state

    def save_memory(self):
        """Uploads current state to Google Drive"""
        if not self.drive_service: return # Cannot save if offline

        try:
            file_metadata = {'name': MEMORY_FILENAME, 'parents': [DRIVE_FOLDER_ID]}
            fh = io.BytesIO(json.dumps(self.state, indent=4).encode('utf-8'))
            media = MediaIoBaseUpload(fh, mimetype='application/json')

            if self.file_id:
                self.drive_service.files().update(
                    fileId=self.file_id,
                    media_body=media
                ).execute()
            else:
                file = self.drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                self.file_id = file.get('id')
        except Exception as e:
            print(f"   ⚠️ Save Memory Failed: {e}")

    def register_trade(self, trade_data):
        self.state['open_bot_trades'].append(trade_data)
        self.save_memory()

    def deregister_trade(self, ticket):
        self.state['open_bot_trades'] = [t for t in self.state['open_bot_trades'] if t['ticket'] != ticket]
        self.save_memory()

    def log_trade(self, trade, reason="OPEN"):
        """
        Logs trade to Google Sheet.
        Reason: OPEN, SL_HIT, TP_HIT, FRIDAY_CLOSE, MANUAL
        """
        if not self.sheets_client: return
        try:
            sheet = self.sheets_client.open_by_url(SHEET_URL)
            try: ws = sheet.worksheet(WORKSHEET_LOGS)
            except: 
                print(f"   📝 Creating new worksheet: {WORKSHEET_LOGS}...")
                ws = sheet.add_worksheet(title=WORKSHEET_LOGS, rows=1000, cols=20)
                # Add Header if new
                ws.append_row(["Ticket", "Strategy", "Signal", "Pair", "Time", "Entry", "SL", "TP", "Vol", "Spread", "Exit", "Close Time", "PnL", "Balance", "Reason"])
            
            status_id = str(trade.get('ticket', 'UNKNOWN'))
            
            row = [
                status_id, 
                trade.get('strategy', 'Unknown'), 
                trade.get('signal', 'Unknown'), 
                trade.get('pair', 'Unknown'),
                trade.get('open_time', ''), 
                trade.get('entry_price', 0), 
                trade.get('stop_loss_price', 0), 
                trade.get('take_profit_price', 0),
                trade.get('volume', 0), 
                trade.get('spread', 0),
                trade.get('exit_price', 0),
                trade.get('close_time', ''),
                trade.get('pnl', 0), 
                f"{self.state.get('current_balance', 0)}",
                reason
            ]
            ws.append_row(row)
            print(f"   📊 Logged trade {status_id} to Sheets.")
        except Exception as e:
            print(f"   ⚠️ Log to Sheet Failed: {e}")