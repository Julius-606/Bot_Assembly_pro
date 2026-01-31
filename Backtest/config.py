import os
from dotenv import load_dotenv

# Load the .env file
load_dotenv()

class Config:
    # MT5 / Broker Settings
    MT5_LOGIN = os.getenv("MT5_LOGIN")
    MT5_PASSWORD = os.getenv("MT5_PASSWORD")
    MT5_SERVER = os.getenv("MT5_SERVER")
    
    # Google Sheets / Cloud Settings
    GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Backtest_Results")
    GOOGLE_CREDS_FILE = os.getenv("GOOGLE_CREDS_FILE", "google_creds.json")
    
    # Validation
    @classmethod
    def validate(cls):
        missing = [k for k, v in cls.__dict__.items() if not k.startswith("__") and v is None]
        if missing:
            print(f"⚠️ Missing config for: {', '.join(missing)}")
            return False
        return True