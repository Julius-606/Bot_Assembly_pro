import os
import json
import streamlit as st
from dotenv import load_dotenv

# 🔐 THE HYBRID LOADER
# Sniffs for .env locally. Streamlit Cloud ignores this and uses its own Secrets.
load_dotenv(override=True)

def get_secret(key, default=None):
    """Hybrid getter: Checks Streamlit Secrets first (Cloud), then Environment (Local)."""
    try:
        # Check Streamlit's internal secrets first
        if key in st.secrets:
            return st.secrets[key]
    except:
        pass
    
    # Fallback to standard environment variables
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

# --- GOOGLE CREDS LOGIC (The Alpha Logic) ---
raw_creds = get_secret("GOOGLE_CREDS")

if raw_creds:
    # Handle both Dict (Streamlit TOML) and String (Local .env)
    if isinstance(raw_creds, dict):
        GOOGLE_CREDS_DICT = dict(raw_creds)
    else:
        try:
            clean_json = str(raw_creds).strip().strip("'").strip('"')
            GOOGLE_CREDS_DICT = json.loads(clean_json)
        except Exception as e:
            print(f"⚠️ CONFIG ERROR: GOOGLE_CREDS string parse failed: {e}")
            GOOGLE_CREDS_DICT = {}
    
    # Fix the private_key formatting if it contains escaped newlines
    if "private_key" in GOOGLE_CREDS_DICT:
        GOOGLE_CREDS_DICT["private_key"] = GOOGLE_CREDS_DICT["private_key"].replace("\\n", "\n")
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