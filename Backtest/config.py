import os
import sys
import json
from dotenv import load_dotenv

# 🔐 LOAD SECRETS (ENV)
try:
    load_dotenv(override=True)
except Exception as e:
    print(f"⚠️ Warning: .env loader encountered an issue: {e}")

# ==============================================================================
# ---- Darwin Backtest Lab Config ----
# ==============================================================================

MT5_LOGIN = int(os.getenv("MT5_LOGIN", 0)) 
MT5_PASSWORD = os.getenv("MT5_PASSWORD")
MT5_SERVER = os.getenv("MT5_SERVER")
MT5_PATH = os.getenv("MT5_PATH")

SHEET_URL = os.getenv("GOOGLE_SHEET_URL")

# --- SIMULATION CONSTANTS ---
HARDCODED_LOT_SIZE = 0.01
CONTRACT_SIZE = 100000 # Standard Forex Lot size

google_json_str = os.getenv("GOOGLE_CREDS")

if google_json_str:
    try:
        clean_json = google_json_str.strip().strip("'").strip('"')
        creds_dict = json.loads(clean_json)
        if "private_key" in creds_dict:
            raw_key = creds_dict["private_key"]
            formatted_key = raw_key.replace("\\n", "\n")
            creds_dict["private_key"] = formatted_key
        GOOGLE_CREDS_DICT = creds_dict
    except json.JSONDecodeError as e:
        print(f"⚠️ CONFIG ERROR: GOOGLE_CREDS is not valid JSON.\n{e}")
        GOOGLE_CREDS_DICT = {}
else:
    print("⚠️ CONFIG ERROR: GOOGLE_CREDS not found in .env")
    GOOGLE_CREDS_DICT = {}

# 💎 THE MARKET LIST (Added Metals and Crypto juice as requested)
USER_DEFAULT_MARKETS = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
    "XAUUSD", "XAGUSD", "BTCUSD", "ETHUSD", "LTCUSD",
    "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "NZDJPY", "CADJPY", "CHFJPY",
    "EURAUD", "EURCAD", "GBPAUD", "GBPCAD", "AUDNZD"
]