# ==============================================================================
# ---- Trend Runner Config v2.4.0 ----
# ==============================================================================
import os
import sys

# ==============================================================================
# 🔐 SECRET SAUCE (CREDENTIALS)
# ==============================================================================

TELEGRAM_BOT_TOKEN = "8141234434:AAFaO3z4NCASSFYwYkH4t1Q4lkA0Us7x_qA" 
TELEGRAM_CHAT_ID = "6882899041"

# --- MT5 SPECIFIC LOGINS ---
MT5_LOGIN = 105473947
MT5_PASSWORD = ":+xLBl3B"
MT5_SERVER = "FBS-Demo"
MT5_PATH = r"C:\Program Files\MetaTrader 5 - Trend Runner\terminal64.exe" 

# --- GOOGLE CLOUD CONFIG ---
GOOGLE_CREDS = r"""
{
  "type": "service_account",
  "project_id": "mt5-algo-bot-logger",
  "private_key_id": "9d9b7fd070ca090bfc87027a9273d5160a5c8420",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCjmyj6r07CHHOi\nFfULyqv/oMG3dvBUCGK8AZqAAZ6ZfuEFhlBuYT1TQ04wK9r4ol8BitIKvCZYMj9b\n0SIYfrOqJx+zGbgRE4m2WezvcmHxNoYPYW5eIgRnetgTniOGjDGcM9+Y8GZInbb8\nBx63z5RNmJdUTcke7v04XQeVSvyX6ug9eQRAjXxIGPExBgkf5ZsZqcVNqXNQPqaE\nLprKwAStLDFNZh3k5rXpqIfVaefGUueA+Wtv4ncTsgOtRmFPRxM1cDDZnQcV07yt\n+vu5aLeFWyssdcT7ZYn6+0Ubxg1msen/wK3KZ+sKUp1enyp09Lx8rOXY8UNG7ita\npQAvrZQFAgMBAAECggEADOboSyamixvDybE6FyE3Qaw7gpycVMApiyKEPNqD156A\nH9epAZ9k/us0oAthVBC39c7tBAA09OkXgoXiTrS1NfKqZw0c7SnRhyId0389dpCC\nb3WTRtSfbMqs/hUPP6XQJr2XgT/aDRl06/iixUOXMixZqMIOnYQiz35UogMdGtzA\n9kFaxXE9AgIoxuj37w1+1LKuMkyL/CNi0/BB0CJhF+AP6AqQ+m5L/f1TN3Bt6VNl\nm7UH3dyZvKlnvn4H4ZuiHhPmbUU6s9sJWt22Mr7dwK21+RiahW/SITDGgkaraPw8\nag/zABaJNpdEXZal8HU8pUuDMyNK0luNiMzQxXNMmQKBgQDaHTvpjknesW0rI/LQ\nIX5uu5dCAd+jDfJXsmHs9kPyEam0nE1OArtkm8Cftn6KbmO1eEwLWsBnsdM4Zpmq\nryHaz+0bvhXwdYgY/DuE39vIVZDp331uq4eqZCMv18XCA6cyKKEimnq9kiKgagL3\nHro5Ryuilo3JvTaLAZJSIJEIvQKBgQDABiTOkui8q7oJlg80ru4049YQFTP8e6Of\nzXk6VhqBeZWLHPtKDqlCdHbTF922lvZktq42txu3Bt7pAEY8RYxmMSE6uDS0IArK\nP5U76Eu8f+ZCM6rMq2lxOossQkViU1H6A6kLdsgsfCOCBXA53rVmN9ZpG44QHIo4\n3jNuIrkg6QKBgCsTYPS0TDR11/iQJfEi3ERkOfAoTJF4PKdDLIHO9QZGpLxtrfq9\nIWMyO22PbhhKythZBLOtXZhdDzjxUmHaKpZ7P/mdpdmSbKl6jwqj51T+SRtXLv9/\nUtC87BITzBOQAyIt0fzyg1ETHlGN/j3tzJtpSd3XW/M+shnr2ojrs5kFAoGBALfh\nqkF/AQwbTm17m1gR494WB5kjFMNFCq0usFYiugMekQvEVwbV/1O5/0ep5RDCg3Ry\nU2Xl9s5P8Aojzx5MY2RAy9dVKnMK9Ao01Q2nJ099Etx2aarQwopBS6C4XYUI0Mmf\n07M8rfebcM1Ds/JWyFL4SYQhdOsMyXgnoAxph+pxAoGBAM35NHood4AoSWrnu2Cg\nn4sLu5Veti/STPUByK1kWpNQ9ZNSJuANoI5nsIIc4xoQq+cLqCbplnGFAYkHx8Lv\nlakli45t4in6vqDDkL6mBe6mBP5erljT5BFLJ09DDvmcT9YOfbgkOFqY/bbWDVBj\n7xHAN8knILhHIPVeiKet0u0z\n-----END PRIVATE KEY-----\n",
  "client_email": "mt5-logger-sa@mt5-algo-bot-logger.iam.gserviceaccount.com",
  "client_id": "101479527830343877881",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/mt5-logger-sa%40mt5-algo-bot-logger.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
"""

SHEET_URL = "https://docs.google.com/spreadsheets/d/1v_5DVdLPntHfPXjHSKK605f5l0m0F4LOTXTsXm1HbIo/edit?usp=sharing"
WORKSHEET_LOGS = "Sheet1"
DRIVE_FOLDER_ID = "16ZJgg2S6NriT84AStjhvM9UI3ckp4rEM"
MEMORY_FILENAME = "trend_runner_memory.json"

DEFAULT_STRATEGY = "TREND_RUNNER"
BOT_IDENTITY = "trendrunner"

# --- RISK MANAGEMENT 🛡️ ---
FIXED_LOT_SIZE = 0.01 
MAX_OPEN_TRADES = 5 
MAX_RISK_PER_TRADE_PCT = 0.05 # 5% Maximum Drawdown per trade

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


# --- STRATEGY PARAMETERS ---
# Controls the sensitivity of the Trend Runner
DEFAULT_PARAMS = {
    "ema_period": 200,
    "rsi_period": 14,
    "atr_period": 14,
    "risk_per_trade": 0.01
}

# --- RUNNER LOGIC (TRAILING) ---
TRAILING_CONFIG = {
    "tp_proximity_threshold": 50, 
    "tp_extension": 200,
    "sl_activation_distance": 100, 
    "sl_distance": 50
}