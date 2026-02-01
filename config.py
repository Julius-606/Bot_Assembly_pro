import os
import json
import streamlit as st
from dotenv import load_dotenv

# 🔐 THE HYBRID LOADER (The Safe Way)
# Sniffs for .env locally. Streamlit Cloud ignores this and uses its own Secrets.
load_dotenv(override=True)

def get_secret(key, default=None):
    """Hybrid getter: Checks Streamlit Secrets first (Cloud), then Environment (Local)."""
    try:
        # Check Streamlit's internal secrets first
        if key in st.secrets:
            val = st.secrets[key]
            # Streamlit Secrets proxy objects can be annoying, let's convert to dict if needed
            if hasattr(val, "to_dict"):
                return val.to_dict()
            return val
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
# We're making this super robust because Streamlit Cloud can be a diva.
raw_creds = get_secret("GOOGLE_CREDS")

GOOGLE_CREDS_DICT = {}

if raw_creds:
    # Scenario A: It's already a dict or a Streamlit AttrDict (from TOML sections)
    if isinstance(raw_creds, dict):
        GOOGLE_CREDS_DICT = dict(raw_creds)
    # Scenario B: It's a string (likely from .env or a single-line Secret)
    elif isinstance(raw_creds, str):
        try:
            # Clean up potential string formatting issues (quotes/whitespace)
            clean_json = raw_creds.strip().strip("'").strip('"')
            GOOGLE_CREDS_DICT = json.loads(clean_json)
        except Exception as e:
            print(f"⚠️ CONFIG ERROR: GOOGLE_CREDS string parse failed: {e}")
    
    # Fix the private_key formatting if it contains escaped newlines
    if "private_key" in GOOGLE_CREDS_DICT:
        GOOGLE_CREDS_DICT["private_key"] = GOOGLE_CREDS_DICT["private_key"].replace("\\n", "\n")
else:
    print("⚠️ CONFIG ERROR: GOOGLE_CREDS not found in Secrets or .env")

# 💎 THE MARKET LIST
USER_DEFAULT_MARKETS = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
    "XAUUSD", "XAGUSD", "BTCUSD", "ETHUSD", "LTCUSD",
    "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "NZDJPY", "CADJPY", "CHFJPY",
    "EURAUD", "EURCAD", "GBPAUD", "GBPCAD", "AUDNZD"
]