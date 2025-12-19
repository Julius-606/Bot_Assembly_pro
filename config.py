# ==============================================================================
# ⚙️ CONFIGURATION
# ==============================================================================

# 💰 MONEY
INITIAL_BALANCE = 50.00 

# 🧠 STRATEGY CONTROL
DEFAULT_STRATEGY = "Auto" # Options: "Auto", "Manual", "LongOnly", "ShortOnly"

# 🤖 TELEGRAM
TELEGRAM_BOT_TOKEN = "8141234434:AAFaO3z4NCASSFYwYkH4t1Q4lkA0Us7x_qA"
TELEGRAM_CHAT_ID = 6882899041

# ☁️ CLOUD
DRIVE_FOLDER_ID = "16ZJgg2S6NriT84AStjhvM9UI3ckp4rEM"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1v_5DVdLPntHfPXjHSKK605f5l0m0F4LOTXTsXm1HbIo/edit?usp=sharing"
WORKSHEET_LOGS = "Sheet1"
WORKSHEET_STATE = "MainFrame_Memory"
MEMORY_CELL = 'A1' 

# 🖼️ IMGBB
IMGBB_API_KEY = "c5e6f0bebf86450c8eedfe83cf5514fa"

# 🧠 STRATEGY PARAMS
DEFAULT_PARAMS = {
    "CANDLE_COUNT": 20,
    "SR_CONFIRMATION_EMA": 20,
    "MOMO_EMA_PERIOD": 20,
    "MOMO_MACD_FAST": 12,
    "MOMO_MACD_SLOW": 26,
    "MOMO_MACD_SIGNAL": 9,
    "MR_BB_PERIOD": 20,
    "MR_BB_STD_DEV": 2.0,
    "MR_RSI_PERIOD": 14,
    "MR_RSI_LOWER": 30,
    "MR_RSI_UPPER": 70,
    "MR_RSI_RANGE_THRESHOLD": 50,
    "REGIME_ADX_THRESHOLD": 25,
    "TRAILING_STOP_POINTS": 50,
    "REGIME_ADX_PERIOD": 14
}

USER_DEFAULT_MARKETS = [
    "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "USD/CAD",
    "AUD/USD", "NZD/USD", "EUR/GBP", "EUR/JPY", "GBP/JPY",
    "AUD/JPY", "EUR/AUD"
]

# 🔐 CREDENTIALS (SENSITIVE)
# NOTE: Ensure indentation is preserved exactly for the key block.
RAW_GOOGLE_CREDS = r"""
{
  "type": "service_account",
  "project_id": "mainframe-v3",
  "private_key_id": "REDACTED_IN_PREVIEW",
  "private_key": "-----BEGIN PRIVATE KEY-----\n[YOUR_PRIVATE_KEY_HERE]\n-----END PRIVATE KEY-----\n",
  "client_email": "mainframe-bot@mainframe-v3.iam.gserviceaccount.com",
  "client_id": "11223344556677889900",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/mainframe-bot%40mainframe-v3.iam.gserviceaccount.com"
}
"""