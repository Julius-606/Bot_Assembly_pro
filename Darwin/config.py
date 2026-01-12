import os
import sys
import json
from dotenv import load_dotenv

# ------------------------------------------------------------------------------
# 🔐 LOAD SECRETS (ENV)
# ------------------------------------------------------------------------------
# Load the .env file from the root directory
load_dotenv()

# ==============================================================================
# ---- Darwin Config ----
# ==============================================================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- MT5 SPECIFIC LOGINS ---
MT5_LOGIN = int(os.getenv("MT5_LOGIN", 0)) 
MT5_PASSWORD = os.getenv("MT5_PASSWORD")
MT5_SERVER = os.getenv("MT5_SERVER")
MT5_PATH = os.getenv("MT5_PATH")

# --- GOOGLE CLOUD CONFIG (DIRECT JSON) ---
# We read the raw JSON string from .env instead of a file path
google_json_str = os.getenv("GOOGLE_CREDS")

if google_json_str:
    try:
        # We parse it here just to make sure it's valid, 
        # then pass the dictionary to cloud.py later (or re-dump it if needed)
        # But wait, CloudManager expects the DICT or credentials object.
        # We will pass the dictionary directly.
        GOOGLE_CREDS_DICT = json.loads(google_json_str)
    except json.JSONDecodeError as e:
        print(f"⚠️ CONFIG ERROR: Your GOOGLE_CREDS in .env is not valid JSON.\n{e}")
        GOOGLE_CREDS_DICT = {}
else:
    print("⚠️ CONFIG ERROR: GOOGLE_CREDS not found in .env")
    GOOGLE_CREDS_DICT = {}

SHEET_URL = "https://docs.google.com/spreadsheets/d/1v_5DVdLPntHfPXjHSKK605f5l0m0F4LOTXTsXm1HbIo/edit?usp=sharing"
WORKSHEET_LOGS = "Sheet3" 
WORKSHEET_COACH = "Coach Darwin"
DRIVE_FOLDER_ID = "16ZJgg2S6NriT84AStjhvM9UI3ckp4rEM"
MEMORY_FILENAME = "darwin_memory.json"

# --- GEMINI AI CONFIG ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

DEFAULT_STRATEGY = "DARWIN"
BOT_IDENTITY = "darwin"

# --- RISK MANAGEMENT 🛡️ ---
FIXED_LOT_SIZE = 0.01 
MAX_OPEN_TRADES = 5 

# --- MARKET CLASSIFICATION ---
USER_DEFAULT_MARKETS = [
    "EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD",
    "ETHUSD", "LTCUSD", "AUDUSD", "NZDUSD", "USDCAD", 
    "USDCHF", "XAGUSD",
    "XRPUSD", "BNBUSD", "DOGEUSD", "SOLUSD"
]

# 24/7 Markets
CRYPTO_MARKETS = [
    "BTCUSD", "ETHUSD", "LTCUSD", 
    "XRPUSD", "BNBUSD", "DOGEUSD", "SOLUSD"
]

DEFAULT_PARAMS = {
    "ema_fast": 9, 
    "ema_slow": 21,      
    "atr_period": 14,
    "risk_per_trade": 0.01
}

TRAILING_CONFIG = {
    "tp_proximity_threshold": 50, 
    "tp_extension": 200,
    "sl_activation_distance": 100, 
    "sl_distance": 50
}