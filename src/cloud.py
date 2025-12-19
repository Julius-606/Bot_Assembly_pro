import json
import io
import base64
import time
import requests
import gspread
import mplfinance as mpf
import pandas as pd
from datetime import datetime
from google.oauth2.service_account import Credentials
from config import RAW_GOOGLE_CREDS, SHEET_URL, WORKSHEET_STATE, MEMORY_CELL, WORKSHEET_LOGS, INITIAL_BALANCE, USER_DEFAULT_MARKETS, DEFAULT_PARAMS, IMGBB_API_KEY, DRIVE_FOLDER_ID, DEFAULT_STRATEGY

class CloudManager:
    def __init__(self):
        self.client = None
        self.state = {}
        self.last_update_id = 0
        self.setup()
        self.load_state()

    def setup(self):
        try:
            creds = Credentials.from_service_account_info(
                json.loads(RAW_GOOGLE_CREDS), 
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            self.client = gspread.authorize(creds)
        except Exception as e:
            print(f"❌ Cloud Auth Failed: {e}")

    def load_state(self):
        try:
            sheet = self.client.open_by_url(SHEET_URL)
            try: ws = sheet.worksheet(WORKSHEET_STATE)
            except: ws = sheet.add_worksheet(title=WORKSHEET_STATE, rows=10, cols=2)
            
            val = ws.acell(MEMORY_CELL).value
            if not val:
                print("⚠️ Brain Empty! Initializing...")
                self.state = {
                    "status": "running",
                    "current_balance": INITIAL_BALANCE,
                    "active_strategy": DEFAULT_STRATEGY,
                    "active_pairs": USER_DEFAULT_MARKETS,
                    "strategy_params": DEFAULT_PARAMS,
                    "open_bot_trades": [],
                    "trade_history": []
                }
            else:
                self.state = json.loads(val)
                print(f"🧠 Brain Loaded. Balance: ${self.state['current_balance']}")
                
        except Exception as e:
            print(f"❌ Load Failed: {e}")
            self.state = {}

    def save_state(self):
        try:
            sheet = self.client.open_by_url(SHEET_URL)
            ws = sheet.worksheet(WORKSHEET_STATE)
            ws.update(MEMORY_CELL, json.dumps(self.state))
        except Exception as e:
            print(f"❌ Save Failed: {e}")

    def log_trade(self, trade):
        try:
            sheet = self.client.open_by_url(SHEET_URL)
            try: ws = sheet.worksheet(WORKSHEET_LOGS)
            except: ws = sheet.add_worksheet(title=WORKSHEET_LOGS, rows=1000, cols=20)
            
            trail_str = f"{trade.get('trail_count',0)}"
            
            row = [
                "CLOSED",
                trade['strategy'],
                trade['signal'],
                trade['pair'],
                trade['open_time'],
                trade['entry_price'],
                trade['stop_loss_price'],
                0, # Spread
                trade['volume'],
                0, # Commission
                0, # Swap
                trade['take_profit_price'],
                trade['exit_price'],
                datetime.now().isoformat(),
                trade['pnl'],
                f"{self.state['current_balance']:.2f}",
                trail_str,
                trade.get('screenshot', 'N/A')
            ]
            
            ws.append_row(row)
            
        except Exception as e:
            print(f"❌ Logging Failed: {e}")

    def upload_chart(self, df, pair, signal, price):
        """Generates chart and uploads to ImgBB"""
        try:
            filename = f"chart_{int(time.time())}.png"
            buf = io.BytesIO()
            
            # Style
            mc = mpf.make_marketcolors(up='green', down='red', inherit=True)
            s  = mpf.make_mpf_style(marketcolors=mc)
            
            # Title with Price (As requested)
            title_text = f"{pair} {signal} @ {price:.5f}"
            
            mpf.plot(df, type='candle', style=s, title=title_text, savefig=buf)
            buf.seek(0)
            
            payload = {
                "key": IMGBB_API_KEY,
                "image": base64.b64encode(buf.getvalue()).decode('utf-8')
            }
            res = requests.post("https://api.imgbb.com/1/upload", data=payload)
            data = res.json()
            return data['data']['url']
            
        except Exception as e:
            print(f"❌ Chart Upload Failed: {e}")
            return "UPLOAD_FAILED"