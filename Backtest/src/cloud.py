import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_CREDS_DICT, SHEET_URL

class CloudManager:
    """The Performance Logger ☁️. Batch logs to the performance show."""
    def __init__(self):
        self.client = None
        self.setup()

    def setup(self):
        try:
            # Using the dict parsed from the single-line JSON in config.py
            creds = Credentials.from_service_account_info(
                GOOGLE_CREDS_DICT, 
                scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            )
            self.client = gspread.authorize(creds)
        except Exception as e:
            print(f"❌ Cloud Setup Failed: {e}")

    def log_test_results(self, data):
        """Batch append to avoid Google's rate-limit 'anti-spam' police."""
        try:
            sheet = self.client.open_by_url(SHEET_URL)
            # Using Sheet4 as per your config
            ws = sheet.worksheet("Sheet4") 
            
            if not ws.get_all_values():
                ws.append_row(["Timestamp", "Pair", "TF", "Signal", "Price", "SL", "TP", "Concoction"])
            
            ws.append_rows(data)
            return True
        except Exception as e:
            print(f"❌ Batch Logging Failed: {e}")
            return False