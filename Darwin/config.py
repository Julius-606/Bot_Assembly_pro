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
WORKSHEET_LOGS = "Sheet4" 
WORKSHEET_COACH = "Coach Darwin"
DRIVE_FOLDER_ID = "16ZJgg2S6NriT84AStjhvM9UI3ckp4rEM"
MEMORY_FILENAME = "darwin_memory.json"

# --- GEMINI AI CONFIG (MULTI-KEY PROTOCOL) ---
GEMINI_API_KEYS = []

# 1. Look for standard list (PROJECT ORBIT STYLE)
orbit_keys = os.getenv("GEMINI_API_KEYS_LIST")
if orbit_keys:
    try:
        GEMINI_API_KEYS = json.loads(orbit_keys)
    except:
        GEMINI_API_KEYS = [k.strip() for k in orbit_keys.split(',') if k.strip()]

# 2. Look for individual keys (Darwin Classic Style)
# 🛠️ ROBUSTNESS FIX: Check if user pasted a comma-list into the singular variable
if not GEMINI_API_KEYS:
    base_key = os.getenv("GEMINI_API_KEY")
    if base_key:
        if ',' in base_key:
            # User put list in singular var - handle it gracefully
            GEMINI_API_KEYS = [k.strip() for k in base_key.split(',') if k.strip()]
        else:
            GEMINI_API_KEYS.append(base_key)
    
    # Also check legacy numbered keys just in case
    for i in range(2, 6): # Check up to 5 keys
        next_key = os.getenv(f"GEMINI_API_KEY_{i}")
        if next_key: GEMINI_API_KEYS.append(next_key)

# Fallback for legacy code
GEMINI_API_KEY = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else None

DEFAULT_STRATEGY = "DARWIN"
BOT_IDENTITY = "darwin"

# --- RISK MANAGEMENT 🛡️ ---
FIXED_LOT_SIZE = 0.02 
MAX_OPEN_TRADES = 8
MAX_RISK_PCT = 0.03 # 🛡️ 3% Hard Cap on Risk per Trade

# 🚫 STRICT BLACKLIST (No Metals, No Crypto)
# Any pair containing these substrings will be rejected immediately.
BLACKLIST_ASSETS = [
    "XAU", "XAG", "XPT", "XPD", # Metals (Gold, Silver, Platinum, Palladium)
    "BTC", "ETH", "LTC", "XRP", "BCH", "EOS", "ADA", "SOL", "DOGE", "SHIB", "DOT", "MATIC", "USDT" # Crypto
]

# --- MARKET CLASSIFICATION ---
# 📉 PURE FOREX MODE (Full Spectrum)
USER_DEFAULT_MARKETS = [
    # The Majors (The VIPs 💅 - Tight Spreads)
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
    
    # The Minors / Crosses (The Volatility Crew 🎢)
    "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "NZDJPY", "CADJPY", "CHFJPY",
    "EURAUD", "EURCAD", "GBPAUD", "GBPCAD", "AUDNZD"
]

# 24/7 Markets (Empty to disable weekend trading logic)
CRYPTO_MARKETS = []

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