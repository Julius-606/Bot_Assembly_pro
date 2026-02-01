import os
import sys
import json
import streamlit as st
from dotenv import load_dotenv

# 🔐 LOAD SECRETS
# Locally, it uses .env. In the cloud, it checks st.secrets automatically.
load_dotenv(override=True)

def get_secret(key, default=None):
    """Hybrid secret getter: Checks Streamlit Secrets first, then ENV."""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except:
        pass
    return os.getenv(key, default)

# ==============================================================================
# ---- Darwin Backtest Lab Config ----
# ==============================================================================

MT5_LOGIN_RAW = get_secret("MT5_LOGIN", "0")
MT5_LOGIN = int(MT5_LOGIN_RAW) if str(MT5_LOGIN_RAW).isdigit() else 0

MT5_PASSWORD = get_secret("MT5_PASSWORD")
MT5_SERVER = get_secret("MT5_SERVER")
MT5_PATH = get_secret("MT5_PATH")

SHEET_URL = get_secret("GOOGLE_SHEET_URL")

# --- SIMULATION CONSTANTS ---
HARDCODED_LOT_SIZE = 0.01
CONTRACT_SIZE = 100000 

google_json_str = get_secret("GOOGLE_CREDS")

if google_json_str:
    try:
        # Clean up any weird quotes from the dashboard paste
        clean_json = str(google_json_str).strip().strip("'").strip('"')
        creds_dict = json.loads(clean_json)
        
        if "private_key" in creds_dict:
            raw_key = creds_dict["private_key"]
            # Fix newline escaping which often breaks in JSON strings
            formatted_key = raw_key.replace("\\n", "\n")
            creds_dict["private_key"] = formatted_key
            
        GOOGLE_CREDS_DICT = creds_dict
    except json.JSONDecodeError as e:
        print(f"⚠️ CONFIG ERROR: GOOGLE_CREDS is not valid JSON.\n{e}")
        GOOGLE_CREDS_DICT = {}
else:
    print("⚠️ CONFIG ERROR: GOOGLE_CREDS not found in Secrets or .env")
    GOOGLE_CREDS_DICT = {}

# 💎 THE MARKET LIST
USER_DEFAULT_MARKETS = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
    "XAUUSD", "XAGUSD", "BTCUSD", "ETHUSD", "LTCUSD",
    "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "NZDJPY", "CADJPY", "CHFJPY",
    "EURAUD", "EURCAD", "GBPAUD", "GBPCAD", "AUDNZD"
]