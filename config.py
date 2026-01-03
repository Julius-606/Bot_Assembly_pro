import os

# ==============================================================================
# 🔐 SECRET SAUCE (CREDENTIALS)
# ==============================================================================

# --- TELEGRAM CONFIG ---
# Get this from @BotFather. Don't share it with your ex. 🤫
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE" 
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID_HERE"

# --- GOOGLE CLOUD CONFIG ---
# Your service account key. This is your VIP pass to Google Drive. 🎟️
GOOGLE_CREDS = {
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "your-private-key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "your-service-account-email",
  "client_id": "your-client-id",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "your-cert-url"
}

# Google Sheets & Drive IDs
SHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"
WORKSHEET_LOGS = "Trade_Logs"
MEMORY_FILENAME = "bot_memory.json"
DRIVE_FOLDER_ID = "YOUR_DRIVE_FOLDER_ID"

# --- STRATEGY DEFAULTS ---
DEFAULT_STRATEGY = "TREND_RUNNER"
USER_DEFAULT_MARKETS = [
    "EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD"
]

DEFAULT_PARAMS = {
    "ema_period": 200,
    "rsi_period": 14,
    "atr_period": 14,
    "risk_per_trade": 0.01
}